#!/usr/bin/env python3
"""core/tuna_tower.py — The Vantage Point

The seiner's tower: rise above the reflection to see into the water.

THE METAPHOR (Casey's insight, exact physics):

  At low viewing angles, water reflects the sky (Fresnel reflection).
  You see the surface, not what's underneath.
  
  A seiner builds a tower (tuna tower, wheelhouse roof) to get a 
  steeper viewing angle. From up there:
    - Surface glare becomes transparent
    - You see THROUGH the water to the fish below
    - Glimpses between waves become a steady view
    
  Applied to models:
  
  Low vantage = consuming model output directly
    - You see the "reflection" — the model's representation of the problem
    - Surface-level: answer, confidence, tokens
    - Can't distinguish signal from glare
    
  High vantage = the tower (meta-layer above both models)
    - Surface glare becomes data (you can see the reflection AS reflection)
    - You see THROUGH the model's representation to the problem structure below
    - The "fish" = the actual shape of the problem space
    
  Seed-mini at the surface:
    - Calm water (45% activation). Very little glare.
    - You see straight through to the answer. Direct.
    - But you ONLY see the fish. You don't see the water, the current, the depth.
    
  Hermes at the surface:
    - Choppy water (93% activation). Tons of glare.
    - All that light looks impressive but you can't see through it.
    - More information but less signal — the reflection IS the noise.
    
  The tower sees BOTH:
    - Seed-mini's calm patch (where the water is clear)
    - Hermes' choppy patch (where the reflection tells you about the surface)
    - The BOUNDARY between calm and choppy = the most informative feature
    
  The boundary between seed-mini's direct path and hermes' activated path
  IS the shape of the problem. That's what neither model can see from the surface.
  
THE ARCHITECTURE:

  Surface layer: model queries (individual receivers at water level)
  Tower layer: the meta-perspective that sees both calm and choppy
  
  The tower doesn't query models. It reads the interference between them.
  The reflection pattern IS the depth map.
  
  What the tower reveals:
    1. FRESNEL ZONES: where models transition from reflective (surface) 
       to transparent (direct). The angle matters more than the resolution.
    2. THERMOCLINES: depth layers where model behavior changes abruptly.
       The "depth cliff" — models work above, fail below.
    3. CURRENT PATTERNS: the flow of reasoning across models.
       Not what each model thinks, but HOW the thinking moves.
    4. BOTTOM TOPOLOGY: the actual shape of the problem space,
       reconstructed from all the surface observations.
    5. SCHOOLING: where multiple models converge (the fish).
       Not consensus — actual structural convergence from different paths.

Usage:
    from core.tuna_tower import TunaTower
    
    tower = TunaTower()
    
    # Rise above the reflection
    view = tower.observations("a*a - a*b + b*b where a=5, b=3", expected="19")
    
    # See the thermoclines
    thermoclines = tower.find_thermoclines(questions)
    
    # Map the bottom topology
    bottom = tower.map_bottom(questions)
"""

from __future__ import annotations

import json, os, re, time, uuid, math, statistics
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple, Set, Any
from collections import defaultdict, Counter
from enum import Enum

import requests

API_KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def _key():
    return open(API_KEY_PATH).read().strip()

def _query(model, prompt, system="", max_tokens=80, temperature=0.0, api_key=None):
    ak = api_key or _key()
    headers = {"Authorization": f"Bearer {ak}", "Content-Type": "application/json"}
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        lat = (time.time() - start) * 1000
        if r.status_code != 200: return {"error": f"HTTP {r.status_code}", "latency_ms": lat}
        d = r.json()
        msg = d["choices"][0]["message"]
        return {
            "content": (msg.get("content") or "").strip(),
            "reasoning_content": (msg.get("reasoning_content") or "").strip(),
            "latency_ms": lat,
            "tokens": d.get("usage", {}).get("total_tokens", 0),
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}

def _extract_num(text):
    if not text: return None
    nums = re.findall(r"-?\d+\.?\d*", text)
    return nums[-1] if nums else None


TOWER_MODELS = {
    "seed-mini":   {"id": "ByteDance/Seed-2.0-mini",     "system": "You are a calculator. Output the result number ONLY.", "mt": 80},
    "gemini-lite":  {"id": "google/gemini-3.1-flash-lite", "system": "You are a calculator. Output the result number ONLY.", "mt": 80},
    "hermes-70b":   {"id": "NousResearch/Hermes-3-Llama-3.1-70B", "system": "Output ONLY the number.", "mt": 80},
    "qwen2.5-72b":  {"id": "Qwen/Qwen2.5-72B-Instruct",   "system": "Output ONLY the number.", "mt": 80},
    "qwen-4b":     {"id": "Qwen/Qwen3.5-4B",              "system": "", "mt": 500, "thinking": True},
}


class WaterState(Enum):
    """What the water looks like from the surface."""
    CALM = "calm"           # Low activation, direct answer — see right through
    CHOPPY = "choppy"       # High activation, lots of glare — hard to see through
    MURKY = "murky"         # Empty/error — can't see anything
    GLEAMING = "gleaming"   # High activation AND correct — the sweet spot


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class SurfaceReading:
    """One model's response — a reading from the water surface."""
    model: str
    answer: Optional[str]
    correct: bool
    water_state: WaterState
    # Activation = surface disturbance (glare)
    activation: float  # 0 = calm, 1 = maximum glare
    # Clarity = how easy to see through (inverse of activation for direct models)
    clarity: float     # 0 = opaque, 1 = transparent
    latency_ms: float = 0
    tokens: int = 0
    raw: str = ""


@dataclass
class FresnelZone:
    """A zone where the viewing angle transitions from reflective to transparent.
    
    Named after the Fresnel equations that govern reflection vs transmission
    at a surface boundary. In our case:
    
    Reflective = model output IS the model's representation (you see the model, not the problem)
    Transparent = model output IS the problem's structure (you see through to the truth)
    
    The zone boundary is where activation transitions.
    """
    models_in_zone: List[str]
    avg_activation: float
    avg_clarity: float
    accuracy: float
    # Is this a calm patch (clear water) or choppy patch (lots of glare)?
    character: str  # "calm_clear", "choppy_opaque", "choppy_clear"


@dataclass
class Thermocline:
    """A depth layer where model behavior changes abruptly.
    
    In oceanography, a thermocline is where temperature drops sharply with depth.
    In model cognition, it's where accuracy drops sharply with problem difficulty.
    
    Above the thermocline: models work. Below: they fail.
    The thermocline IS the depth cliff. Mapping it tells you the model's true depth.
    """
    model: str
    depth_level: int  # How hard was the problem when it failed?
    accuracy_above: float  # % correct above this depth
    accuracy_below: float  # % correct below this depth
    drop_pp: float         # Percentage point drop
    # What kind of problem is at this depth?
    failing_tasks: List[str] = field(default_factory=list)
    passing_tasks: List[str] = field(default_factory=list)


@dataclass
class BottomTopology:
    """The actual shape of the problem space — the bottom topology.
    
    Reconstructed from ALL surface observations:
      - Where models agree = flat bottom (easy terrain)
      - Where models disagree = ridges (hard terrain)  
      - Where all models fail = canyons (the depth cliffs)
      - Where all models succeed = plateaus (the safe zones)
    """
    feature_type: str  # "plateau", "ridge", "canyon", "slope", "basin"
    question_pattern: str  # What kind of questions produce this feature
    models_that_see: List[str]  # Which models can navigate this terrain
    models_that_crash: List[str]  # Which models hit bottom here
    depth: float  # How deep (0=surface easy, 1=deep hard)
    width: int   # How many questions of this type (prevalence)


@dataclass
class School:
    """Where multiple models converge on the same answer from different paths.
    
    In fishing, you see the school from the tower — all the fish moving together.
    It's not consensus (voting). It's structural convergence — they're all 
    swimming in the same current because the current IS the structure.
    
    A school is: multiple models independently arrive at the same answer,
    from different cognitive pathways, with different activation patterns.
    That's not coincidence — that's the structure of the problem pulling them.
    """
    answer: str
    correct: bool
    models: List[str]
    # Did they arrive via the same path or different paths?
    pathways_converge: bool
    # How different are their activation patterns?
    activation_diversity: float  # 0 = identical, 1 = completely different
    # How strong is the school? (pull of the underlying structure)
    structural_strength: float  # 0 = coincidence, 1 = undeniable


@dataclass
class TowerView:
    """The complete view from the tuna tower.
    
    Everything seen from above the reflection line.
    """
    view_id: str
    question: str
    expected: Optional[str]
    
    # Surface readings from each model
    readings: List[SurfaceReading] = field(default_factory=list)
    
    # Fresnel zones (calm vs choppy patches)
    fresnel_zones: List[FresnelZone] = field(default_factory=list)
    
    # Schools (structural convergence points)
    schools: List[School] = field(default_factory=list)
    
    # The boundary between calm and choppy
    boundary: Optional[Dict] = None
    
    # What the tower sees that the surface can't
    below_surface: Optional[Dict] = None
    
    # Summary
    n_models: int = 0
    n_correct: int = 0
    water_character: str = ""  # Overall water state
    tower_insight: str = ""  # What the tower reveals


# ─── The Tower ─────────────────────────────────────────────────────────────────

class TunaTower:
    """The seiner's tower — rise above the reflection to see into the water.
    
    The tower is NOT another model. It's not smarter or bigger.
    It's a DIFFERENT VANTAGE POINT on the same information.
    
    From the surface, you see one model's reflection.
    From the tower, you see the PATTERN of reflections across all models.
    The pattern reveals the bottom topology — the actual problem space.
    """
    
    def __init__(self, models: Dict = None, api_key: str = None):
        self.models = models or TOWER_MODELS
        self.api_key = api_key
    
    # ─── OBSERVE (single question) ─────────────────────────────────────────
    
    def observe(self, question: str, expected: str = None,
                models: List[str] = None) -> TowerView:
        """Take readings from the surface, then observe from the tower.
        
        1. CAPTURE: Each model produces a surface reading
        2. CLASSIFY: Is the water calm or choppy for each model?
        3. FIND ZONES: Group models by water state (Fresnel zones)
        4. FIND SCHOOLS: Where do models structurally converge?
        5. FIND BOUNDARY: The transition between calm and choppy
        6. SEE BELOW: What the tower reveals that surface can't
        """
        model_keys = models or list(self.models.keys())
        
        view = TowerView(
            view_id=str(uuid.uuid4())[:8],
            question=question,
            expected=expected,
            n_models=len(model_keys),
        )
        
        # 1. Capture surface readings
        for mk in model_keys:
            if mk not in self.models: continue
            mi = self.models[mk]
            resp = _query(mi["id"], question, system=mi.get("system", ""),
                         max_tokens=mi.get("mt", 80), api_key=self.api_key)
            
            content = resp.get("content", "")
            reasoning = resp.get("reasoning_content", "")
            text = content if content else reasoning
            answer = _extract_num(content) or _extract_num(reasoning)
            
            correct = False
            if expected and answer:
                try: correct = abs(float(answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                except: pass
            
            # Measure activation (surface disturbance)
            # More text = more activation = more glare
            activation = min(1.0, len(text) / 500)
            
            # Clarity: direct models (short answer) are clear water
            # Thinking models (long reasoning) are churning up the water
            if answer and len(text) < 20:
                clarity = 0.95  # Crystal clear — see right to the bottom
                water = WaterState.CALM
            elif answer and correct and activation < 0.3:
                clarity = 0.9
                water = WaterState.CALM
            elif answer and correct and activation > 0.3:
                clarity = 0.6  # Correct but lots of glare
                water = WaterState.GLEAMING
            elif answer and not correct and activation > 0.3:
                clarity = 0.2  # Wrong AND lots of glare — opaque
                water = WaterState.CHOPPY
            elif not answer:
                clarity = 0.0
                water = WaterState.MURKY
            else:
                clarity = 0.5
                water = WaterState.CHOPPY
            
            view.readings.append(SurfaceReading(
                model=mk, answer=answer, correct=correct,
                water_state=water, activation=activation, clarity=clarity,
                latency_ms=resp.get("latency_ms", 0),
                tokens=resp.get("tokens", 0),
                raw=text[:200],
            ))
            if correct: view.n_correct += 1
        
        # 2. Classify Fresnel zones
        view.fresnel_zones = self._find_fresnel_zones(view.readings)
        
        # 3. Find schools
        view.schools = self._find_schools(view.readings)
        
        # 4. Find the boundary
        view.boundary = self._find_boundary(view.readings)
        
        # 5. See below the surface
        view.below_surface = self._see_below(view)
        
        # 6. Overall water character
        calm_count = sum(1 for r in view.readings if r.water_state == WaterState.CALM)
        choppy_count = sum(1 for r in view.readings if r.water_state == WaterState.CHOPPY)
        if calm_count > choppy_count:
            view.water_character = "mostly calm — good conditions for surface fishing"
        elif choppy_count > calm_count:
            view.water_character = "mostly choppy — need the tower to see through the glare"
        else:
            view.water_character = "mixed conditions — some clear patches, some glare"
        
        # 7. Tower insight
        view.tower_insight = self._generate_insight(view)
        
        return view
    
    # ─── THERMOCLINES (multi-question depth profiling) ─────────────────────
    
    def find_thermoclines(self, questions: List[Tuple[str, str, int]],
                          models: List[str] = None) -> List[Thermocline]:
        """Find depth thermoclines for each model.
        
        Questions must include a difficulty level (1-5).
        The thermocline is where accuracy drops sharply with difficulty.
        
        Like finding the ocean thermocline — the depth where temperature
        drops sharply. Above = warm surface currents (easy problems).
        Below = cold deep water (hard problems the model can't handle).
        """
        # Collect accuracy by model × difficulty
        model_accuracy = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))
        
        for question, expected, difficulty in questions:
            for mk in (models or list(self.models.keys())):
                if mk not in self.models: continue
                mi = self.models[mk]
                resp = _query(mi["id"], question, system=mi.get("system", ""),
                             max_tokens=mi.get("mt", 80), api_key=self.api_key)
                
                content = resp.get("content", "")
                reasoning = resp.get("reasoning_content", "")
                answer = _extract_num(content) or _extract_num(reasoning)
                
                correct = False
                if expected and answer:
                    try: correct = abs(float(answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                    except: pass
                
                model_accuracy[mk][difficulty]["total"] += 1
                if correct:
                    model_accuracy[mk][difficulty]["correct"] += 1
        
        # Find thermoclines
        thermoclines = []
        for mk, levels in model_accuracy.items():
            sorted_levels = sorted(levels.keys())
            for i in range(len(sorted_levels) - 1):
                d1 = sorted_levels[i]
                d2 = sorted_levels[i + 1]
                
                acc1 = levels[d1]["correct"] / max(levels[d1]["total"], 1) * 100
                acc2 = levels[d2]["correct"] / max(levels[d2]["total"], 1) * 100
                drop = acc1 - acc2
                
                if drop > 20:  # 20pp drop = thermocline
                    thermoclines.append(Thermocline(
                        model=mk,
                        depth_level=d2,
                        accuracy_above=round(acc1, 1),
                        accuracy_below=round(acc2, 1),
                        drop_pp=round(drop, 1),
                    ))
        
        return sorted(thermoclines, key=lambda t: -t.drop_pp)
    
    # ─── BOTTOM TOPOLOGY (multi-question map) ──────────────────────────────
    
    def map_bottom(self, questions: List[Tuple[str, str]],
                   models: List[str] = None) -> List[BottomTopology]:
        """Map the bottom topology from surface observations.
        
        Multiple questions = multiple sonar pings from different angles.
        The aggregate reveals the shape of the problem space.
        """
        results = []  # (question, model, answer, correct)
        
        for question, expected in questions:
            for mk in (models or list(self.models.keys())):
                if mk not in self.models: continue
                mi = self.models[mk]
                resp = _query(mi["id"], question, system=mi.get("system", ""),
                             max_tokens=mi.get("mt", 80), api_key=self.api_key)
                
                content = resp.get("content", "")
                reasoning = resp.get("reasoning_content", "")
                answer = _extract_num(content) or _extract_num(reasoning)
                
                correct = False
                if expected and answer:
                    try: correct = abs(float(answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                    except: pass
                
                results.append((question, mk, answer, correct))
        
        # Classify each question by its topology
        topologies = []
        question_models = defaultdict(lambda: {"see": [], "crash": []})
        
        for q, mk, ans, correct in results:
            if correct:
                question_models[q]["see"].append(mk)
            else:
                question_models[q]["crash"].append(mk)
        
        for q, data in question_models.items():
            n_see = len(data["see"])
            n_crash = len(data["crash"])
            n_total = n_see + n_crash
            
            if n_see == n_total:
                feature = "plateau"  # All models navigate this terrain
                depth = 0.0
            elif n_see == 0:
                feature = "canyon"  # All models crash — the deepest terrain
                depth = 1.0
            elif n_see > n_crash:
                feature = "slope"  # Most models navigate, some crash
                depth = 1 - (n_see / n_total)
            elif n_crash > n_see:
                feature = "ridge"  # Most models crash, some navigate
                depth = 1 - (n_see / n_total)
            else:
                feature = "basin"  # 50/50 — the boundary terrain
                depth = 0.5
            
            topologies.append(BottomTopology(
                feature_type=feature,
                question_pattern=q[:60],
                models_that_see=data["see"],
                models_that_crash=data["crash"],
                depth=round(depth, 2),
                width=1,
            ))
        
        return topologies
    
    # ─── REPORTING ─────────────────────────────────────────────────────────
    
    def report(self, view: TowerView) -> str:
        lines = [
            f"{'='*60}",
            f" tuna tower — ABOVE THE REFLECTION",
            f"{'='*60}",
            f"Question: {view.question[:70]}",
            f"Expected: {view.expected}",
            f"Models: {view.n_models} | Correct: {view.n_correct}/{view.n_models}",
            f"Water: {view.water_character}",
            "",
        ]
        
        # Surface readings
        lines.append("SURFACE READINGS (what you see from the boat):")
        for r in view.readings:
            sym = "✓" if r.correct else "✗"
            ws = r.water_state.value
            clarity_bar = "░" * int((1 - r.clarity) * 10) + "▓" * int(r.clarity * 10)
            act_bar = "·" * int((1 - r.activation) * 10) + "∘" * int(r.activation * 10)
            lines.append(f"  {sym} {r.model:12s} [{ws:9s}] clarity={r.clarity:.1f} activation={r.activation:.1f} "
                        f"answer={r.answer or 'EMPTY':6s}")
        
        # Fresnel zones
        if view.fresnel_zones:
            lines.append(f"\nFRESNEL ZONES (calm vs choppy patches):")
            for fz in view.fresnel_zones:
                lines.append(f"  {fz.character:15s}: {', '.join(fz.models_in_zone)} "
                            f"activation={fz.avg_activation:.2f} clarity={fz.avg_clarity:.2f} "
                            f"accuracy={fz.accuracy:.0%}")
        
        # Schools
        if view.schools:
            lines.append(f"\nSCHOOLS (structural convergence from the tower):")
            for s in view.schools:
                conv = "convergent paths" if s.pathways_converge else "divergent paths"
                strength_bar = "🐟" * int(s.structural_strength * 5)
                lines.append(f"  {strength_bar} answer={s.answer} ← {', '.join(s.models)} "
                            f"({conv}, diversity={s.activation_diversity:.2f}, "
                            f"strength={s.structural_strength:.2f})")
        
        # Boundary
        if view.boundary:
            b = view.boundary
            lines.append(f"\nBOUNDARY (calm↔choppy transition):")
            lines.append(f"  Calm side: {b.get('calm_models', [])}")
            lines.append(f"  Choppy side: {b.get('choppy_models', [])}")
            lines.append(f"  The boundary IS the problem structure")
        
        # Below surface
        if view.below_surface:
            bs = view.below_surface
            lines.append(f"\nBELOW THE SURFACE (tower only):")
            for key, val in bs.items():
                lines.append(f"  {key}: {val}")
        
        # Tower insight
        if view.tower_insight:
            lines.append(f"\n🗼 TOWER INSIGHT:")
            lines.append(f"  {view.tower_insight}")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    # ─── Internal ──────────────────────────────────────────────────────────
    
    def _find_fresnel_zones(self, readings: List[SurfaceReading]) -> List[FresnelZone]:
        """Group models by water state."""
        zones = defaultdict(list)
        for r in readings:
            zones[r.water_state].append(r)
        
        result = []
        for ws, rs in zones.items():
            avg_act = statistics.mean(r.activation for r in rs)
            avg_clar = statistics.mean(r.clarity for r in rs)
            acc = sum(1 for r in rs if r.correct) / len(rs)
            
            if ws == WaterState.CALM:
                character = "calm_clear"
            elif ws == WaterState.GLEAMING:
                character = "choppy_clear"
            elif ws == WaterState.CHOPPY:
                character = "choppy_opaque"
            else:
                character = "murky_opaque"
            
            result.append(FresnelZone(
                models_in_zone=[r.model for r in rs],
                avg_activation=round(avg_act, 2),
                avg_clarity=round(avg_clar, 2),
                accuracy=round(acc, 2),
                character=character,
            ))
        
        return result
    
    def _find_schools(self, readings: List[SurfaceReading]) -> List[School]:
        """Find structural convergence points."""
        answer_models = defaultdict(list)
        for r in readings:
            if r.answer:
                answer_models[r.answer].append(r)
        
        schools = []
        for answer, rs in answer_models.items():
            if len(rs) < 2: continue
            
            # Do they arrive via different activation levels?
            activations = [r.activation for r in rs]
            diversity = statistics.variance(activations) if len(activations) > 1 else 0
            
            correct = any(r.correct for r in rs)
            pathways_converge = diversity < 0.1  # Similar activation = same path
            
            # Structural strength = number of models × correctness × diversity
            # High diversity + high count + correct = strong school (structure pulling different minds)
            strength = len(rs) * (1 if correct else 0.3) * (1 + diversity)
            strength = min(1.0, strength / 4)
            
            schools.append(School(
                answer=answer,
                correct=correct,
                models=[r.model for r in rs],
                pathways_converge=pathways_converge,
                activation_diversity=round(diversity, 3),
                structural_strength=round(strength, 2),
            ))
        
        return sorted(schools, key=lambda s: -s.structural_strength)
    
    def _find_boundary(self, readings: List[SurfaceReading]) -> Optional[Dict]:
        """Find the boundary between calm and choppy models."""
        calm = [r for r in readings if r.water_state in (WaterState.CALM, WaterState.GLEAMING)]
        choppy = [r for r in readings if r.water_state == WaterState.CHOPPY]
        
        if not calm or not choppy:
            return None
        
        return {
            "calm_models": [r.model for r in calm],
            "calm_avg_activation": round(statistics.mean(r.activation for r in calm), 2),
            "choppy_models": [r.model for r in choppy],
            "choppy_avg_activation": round(statistics.mean(r.activation for r in choppy), 2),
            "activation_gap": round(
                statistics.mean(r.activation for r in choppy) - 
                statistics.mean(r.activation for r in calm), 2),
            "interpretation": "Calm models see through directly. Choppy models see the surface glare. The gap is the problem's reflective index.",
        }
    
    def _see_below(self, view: TowerView) -> Dict:
        """What the tower sees below the surface."""
        correct_models = [r for r in view.readings if r.correct]
        wrong_models = [r for r in view.readings if not r.correct]
        
        below = {}
        
        # How deep is the water? (How hard is the problem?)
        if view.n_models > 0:
            below["depth_estimate"] = f"{(1 - view.n_correct/view.n_models)*100:.0f}% of models crashed — water is {'shallow' if view.n_correct > view.n_models/2 else 'deep'}"
        
        # Is the answer visible from the surface?
        correct_calm = [r for r in correct_models if r.water_state == WaterState.CALM]
        if correct_calm:
            below["direct_sightings"] = f"{', '.join(r.model for r in correct_calm)} saw the fish directly through calm water"
        
        # What's the glare telling us?
        wrong_active = [r for r in wrong_models if r.activation > 0.3]
        if wrong_active:
            below["glare_analysis"] = f"{', '.join(r.model for r in wrong_active)} are seeing surface glare — they're processing the reflection, not the fish. The glare pattern reveals the model's cognitive surface properties."
        
        # Structural school?
        strong_schools = [s for s in view.schools if s.structural_strength > 0.5]
        if strong_schools:
            s = strong_schools[0]
            below["school_depth"] = f"Structural convergence at answer {s.answer} — {len(s.models)} models swimming together despite {s.activation_diversity:.2f} activation diversity. This IS the current, not coincidence."
        
        return below
    
    def _generate_insight(self, view: TowerView) -> str:
        """Generate the tower's insight — what only the vantage point reveals."""
        correct = [r for r in view.readings if r.correct]
        wrong = [r for r in view.readings if not r.correct]
        
        if not correct:
            return "No model can see through the water here. The bottom is too deep for any surface observation. This is a canyon — send a diver (deeper model or decomposition)."
        
        correct_calm = [r for r in correct if r.water_state == WaterState.CALM]
        correct_choppy = [r for r in correct if r.water_state in (WaterState.GLEAMING, WaterState.CHOPPY)]
        
        if correct_calm and wrong:
            calm_names = ", ".join(r.model for r in correct_calm)
            wrong_names = ", ".join(r.model for r in wrong)
            return (f"The water is calm for {calm_names} — they see straight through. "
                    f"But {wrong_names} are fighting surface glare. "
                    f"The tower shows: the problem is actually simple (the calm models prove it), "
                    f"but some models can't see past their own reflection.")
        
        if correct_calm and not wrong:
            return f"Crystal clear water. All models see through. This is a plateau — flat, easy terrain."
        
        if correct_choppy and wrong:
            return (f"Choppy water but some models found the fish anyway. "
                    f"The churning doesn't mean the fish aren't there — it means some models "
                    f"create their own turbulence. The tower sees: trust the calm readings, "
                    f"the choppy ones are seeing their own wake.")
        
        return "Mixed conditions. The tower shows layers of clarity — some models at some depths can see through, others can't."


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="Tuna Tower — see through the reflection")
    p.add_argument("question", nargs="?", default="a*a - a*b + b*b where a=5, b=3")
    p.add_argument("--expected", default=None)
    p.add_argument("--map-bottom", help="JSON file with [{question, expected}]")
    p.add_argument("--output", default=None)
    p.add_argument("--models", nargs="+", default=None)
    args = p.parse_args()
    
    tower = TunaTower()
    
    if args.map_bottom:
        with open(args.map_bottom) as f:
            questions = json.load(f)
        q_list = [(q["question"], q.get("expected")) for q in questions]
        topo = tower.map_bottom(q_list, models=args.models)
        
        print(f"BOTTOM TOPOLOGY ({len(topo)} features):")
        for t in sorted(topo, key=lambda t: t.depth):
            see = ", ".join(t.models_that_see) or "none"
            crash = ", ".join(t.models_that_crash) or "none"
            print(f"  {t.feature_type:8s} depth={t.depth:.2f}: see=[{see}] crash=[{crash}]")
            print(f"    {t.question_pattern}")
    else:
        view = tower.observe(args.question, expected=args.expected, models=args.models)
        print(tower.report(view))

if __name__ == "__main__":
    main()
