#!/usr/bin/env python3
"""core/functional_imaging.py — fMRI for Model Cognition

THE INSIGHT (Casey's analogy):
  CT scan  = structural imaging. What IS there. (Answer: 19)
  fMRI     = functional imaging. What HAPPENED. (Trace: activated computation, 
             uncertainty at step 4, correction at step 6, confidence trajectory)

  The slice plane matters more than the resolution.
  
  A CT scan slices through SPACE — where is the tumor?
  An fMRI slices through FUNCTION — what is the brain DOING?
  
  A single model query slices through ACCURACY — did you get the right answer?
  A reasoning trace slices through COGNITION — what did you THINK ABOUT?
  
  The kaleidoscope doesn't get "better answers." 
  It reveals the FUNCTIONAL TOPOLOGY of the problem space.
  
  Multiple models × reasoning traces = multi-subject fMRI
  You don't just see what each model answered — 
  you see the ACTIVATION MAP of the problem space itself.

WHAT THIS ENABLES:
  - Hot spots: parts of the problem that light up every model (high activation)
  - Cold spots: parts no model activates (blind spots, not just wrong answers)
  - Temporal sequences: the ORDER of activation (diagnostic, not just result)
  - Connectivity: which concepts activate TOGETHER (semantic network)
  - Deactivation: what a model STOPPED thinking about (suppression = data)
  - Cross-subject registration: mapping different models' cognition to a shared space
  
THE SPLINE METAPHOR:
  CT slices are flat planes through anatomy.
  fMRI slices through TIME × ACTIVATION × LOCATION.
  
  Our functional imaging slices through:
    STEP × CONFIDENCE × CONCEPT × MODEL × AGREEMENT
  
  The "spline" is the interpolation between these slices —
  reconstructing the continuous topology from discrete samples.
  
  Just as fMRI reconstructs neural activity from blood flow samples,
  we reconstruct cognitive topology from trace samples.

Usage:
    from core.functional_imaging import FunctionalImager
    
    fi = FunctionalImager()
    
    # Single-subject "scan"
    scan = fi.scan("a*a - a*b + b*b where a=5, b=3", expected="19")
    
    # Multi-subject "study" (the fMRI experiment)
    study = fi.study([
        ("a*a - a*b + b*b where a=5, b=3", "19"),
        ("(a+b)*(a-b) where a=7, b=2", "45"),
        ("What comes next: 1, 7, 19, 37, 61?", "91"),
    ])
    
    # The activation map
    activation = fi.activation_map(study)
    
    # Temporal profile
    temporal = fi.temporal_profile(scan)
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

def _query(model, prompt, system="", max_tokens=500, temperature=0.0, api_key=None):
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
            "model": model,
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}

def _extract_num(text):
    if not text: return None
    nums = re.findall(r"-?\d+\.?\d*", text)
    return nums[-1] if nums else None


# ─── Models ────────────────────────────────────────────────────────────────────

SCAN_MODELS = {
    "seed-mini":   {"id": "ByteDance/Seed-2.0-mini",     "type": "direct",   "system": "You are a calculator. Output the result number ONLY."},
    "gemini-lite":  {"id": "google/gemini-3.1-flash-lite", "type": "direct",   "system": "You are a calculator. Output the result number ONLY."},
    "hermes-70b":   {"id": "NousResearch/Hermes-3-Llama-3.1-70B", "type": "direct", "system": ""},
    "qwen2.5-72b":  {"id": "Qwen/Qwen2.5-72B-Instruct",   "type": "direct",   "system": "Output ONLY the final number."},
    "qwen-4b":     {"id": "Qwen/Qwen3.5-4B",              "type": "thinking", "system": "", "max_tokens": 600},
    "qwen-9b":     {"id": "Qwen/Qwen3.5-9B",              "type": "thinking", "system": "", "max_tokens": 800},
}


# ─── Data Structures ──────────────────────────────────────────────────────────

class ActivationType(Enum):
    """What kind of cognitive activation happened at this step?"""
    COMPUTE = "compute"           # Numerical computation
    VERIFY = "verify"             # Verification step
    EXPLORE = "explore"           # Exploring alternatives
    REJECT = "reject"             # Rejecting a path
    CONFUSE = "confuse"           # Uncertainty / hesitation
    CORRECT = "correct"           # Self-correction
    METACOGNITIVE = "metacognitive"  # Thinking about thinking
    OVERCONFIDENT = "overconfident"  # High confidence, wrong answer
    SUPPRESSED = "suppressed"     # Topic mentioned then dropped

@dataclass
class Voxel:
    """A single unit of cognitive activation — the voxel of our fMRI.
    
    In neuroimaging, a voxel is a 3D pixel representing neural activity.
    Here, it's a multi-dimensional point in cognition space:
      (model, step, concept, activation_strength, confidence, time)
    """
    voxel_id: str
    model: str
    step_index: int
    activation_type: ActivationType
    # What concepts are "lit up" in this voxel
    concepts: List[str] = field(default_factory=list)
    # Numbers mentioned (the "neural activation" in math space)
    numbers: List[str] = field(default_factory=list)
    # Activation strength (0.0 to 1.0)
    strength: float = 0.5
    # Confidence at this point
    confidence: float = 0.7
    # The raw text
    content: str = ""
    # Temporal position (latency up to this step)
    time_ms: float = 0

@dataclass  
class CognitiveSlice:
    """A single "slice" through the cognitive space — like one fMRI slice.
    
    All voxels at a given step across all models.
    """
    slice_index: int
    question: str
    voxels: List[Voxel] = field(default_factory=list)
    # Agreement at this slice
    agreement: float = 0.0
    # What's activated vs suppressed at this depth
    hot_concepts: List[str] = field(default_factory=list)
    cold_concepts: List[str] = field(default_factory=list)

@dataclass
class ActivationMap:
    """The full activation map — the fMRI of a question across models.
    
    This is the reconstructed topology. It shows:
      - WHERE models agree (hot spots)
      - WHERE models disagree (cold spots / boundaries)
      - HOW activation flows through time (temporal profile)
      - WHAT is suppressed (deactivation = data)
      - WHICH concepts are connected (connectivity)
    """
    map_id: str
    question: str
    expected: Optional[str]
    
    # The slices (one per cognitive step across all models)
    slices: List[CognitiveSlice] = field(default_factory=list)
    
    # Hot spots: concepts that activate strongly across models
    hot_spots: Dict[str, float] = field(default_factory=dict)  # concept → strength
    
    # Cold spots: concepts no model activated
    cold_spots: List[str] = field(default_factory=list)
    
    # Deactivations: what models stopped thinking about
    deactivations: List[Dict] = field(default_factory=list)
    
    # Connectivity: concepts that co-activate
    connectivity: Dict[str, List[str]] = field(default_factory=dict)
    
    # Temporal profile: how activation changes over time
    temporal_profile: List[Dict] = field(default_factory=list)
    
    # Cross-model registration: shared cognitive space
    registration: Dict[str, Dict] = field(default_factory=dict)
    
    # Summary statistics
    n_models: int = 0
    n_voxels: int = 0
    total_activation: float = 0.0
    peak_activation: float = 0.0
    
    # The spline: interpolated topology between slices
    spline_points: List[Dict] = field(default_factory=list)

@dataclass
class ScanResult:
    """Result of scanning one question through all models."""
    scan_id: str
    question: str
    expected: Optional[str]
    
    # Raw traces from each model
    traces: Dict[str, Dict] = field(default_factory=dict)  # model → {content, reasoning, steps}
    
    # The activation map
    activation_map: Optional[ActivationMap] = None
    
    # Meta
    n_models: int = 0
    n_correct: int = 0
    latency_ms: float = 0

@dataclass
class StudyResult:
    """Result of a multi-question study (the full fMRI experiment)."""
    study_id: str
    n_questions: int
    scans: List[ScanResult] = field(default_factory=list)
    
    # Aggregate activation across all questions
    aggregate_hot_spots: Dict[str, float] = field(default_factory=dict)
    aggregate_cold_spots: List[str] = field(default_factory=list)
    
    # Per-model activation profiles
    model_profiles: Dict[str, Dict] = field(default_factory=dict)
    
    # Cross-question connectivity
    cross_question_connectivity: Dict[str, List[str]] = field(default_factory=dict)


# ─── The Functional Imager ─────────────────────────────────────────────────────

class FunctionalImager:
    """fMRI for model cognition.
    
    The difference between this and the kaleidoscope:
      Kaleidoscope → answers + harmonics (structural)
      FunctionalImager → activation topology (functional)
      
    The kaleidoscope asks: "Do models agree?"
    The imager asks: "What is the SHAPE of the problem in cognition space?"
    
    The slice plane is different:
      Kaleidoscope slices through ACCURACY
      Imager slices through ACTIVATION × TEMPORAL × CONCEPTUAL
    
    The reconstruction is different:
      Kaleidoscope reconstructs consensus
      Imager reconstructs topology — the true shape of the problem
    """
    
    def __init__(self, models: Dict = None, api_key: str = None):
        self.models = models or SCAN_MODELS
        self.api_key = api_key
    
    # ─── SINGLE SCAN ───────────────────────────────────────────────────────
    
    def scan(self, question: str, expected: str = None,
             models: List[str] = None) -> ScanResult:
        """Scan one question through all models. Produce activation map."""
        
        model_keys = models or list(self.models.keys())
        scan = ScanResult(
            scan_id=str(uuid.uuid4())[:8],
            question=question,
            expected=expected,
            n_models=len(model_keys),
        )
        
        total_start = time.time()
        
        # Collect traces from all models
        for mk in model_keys:
            if mk not in self.models: continue
            model_info = self.models[mk]
            mid = model_info["id"]
            mtype = model_info.get("type", "direct")
            sys = model_info.get("system", "")
            mt = model_info.get("max_tokens", 200 if mtype == "thinking" else 80)
            
            resp = _query(mid, question, system=sys, max_tokens=mt, api_key=self.api_key)
            
            content = resp.get("content", "")
            reasoning = resp.get("reasoning_content", "")
            text = content if content else reasoning
            answer = _extract_num(content) or _extract_num(reasoning)
            
            # Parse steps
            steps = self._parse_steps(text, mtype == "thinking")
            
            correct = False
            if expected and answer:
                try: correct = abs(float(answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                except: pass
            
            scan.traces[mk] = {
                "content": content[:500],
                "reasoning_content": reasoning[:2000],
                "answer": answer,
                "correct": correct,
                "steps": steps,
                "n_steps": len(steps),
                "latency_ms": resp.get("latency_ms", 0),
                "model_type": mtype,
            }
            if correct: scan.n_correct += 1
        
        scan.latency_ms = (time.time() - total_start) * 1000
        
        # Build activation map
        scan.activation_map = self._build_activation_map(scan)
        
        return scan
    
    # ─── MULTI-QUESTION STUDY ──────────────────────────────────────────────
    
    def study(self, questions: List[Tuple[str, str]], 
              models: List[str] = None) -> StudyResult:
        """Run a multi-question fMRI study. Aggregate activation across questions."""
        
        result = StudyResult(
            study_id=str(uuid.uuid4())[:8],
            n_questions=len(questions),
        )
        
        for i, (q, expected) in enumerate(questions):
            print(f"  Scan [{i+1}/{len(questions)}]: {q[:50]}...", flush=True)
            scan = self.scan(q, expected=expected, models=models)
            result.scans.append(scan)
        
        # Aggregate
        result.aggregate_hot_spots, result.aggregate_cold_spots = \
            self._aggregate_activation(result.scans)
        result.model_profiles = self._build_model_profiles(result.scans)
        result.cross_question_connectivity = self._cross_question_connectivity(result.scans)
        
        return result
    
    # ─── ACTIVATION MAP BUILDER ─────────────────────────────────────────────
    
    def _build_activation_map(self, scan: ScanResult) -> ActivationMap:
        """Build the activation map from all model traces.
        
        This is the fMRI reconstruction:
          1. Parse each trace into voxels (activation units)
          2. Register all models to shared cognitive space
          3. Compute hot/cold spots (what lights up vs what doesn't)
          4. Build connectivity (what co-activates)
          5. Build temporal profile (how activation changes over time)
          6. Spline between slices (interpolate the topology)
        """
        am = ActivationMap(
            map_id=scan.scan_id,
            question=scan.question,
            expected=scan.expected,
        )
        
        # 1. Parse voxels from each model
        all_voxels: List[Voxel] = []
        max_steps = 0
        
        for mk, trace in scan.traces.items():
            steps = trace.get("steps", [])
            max_steps = max(max_steps, len(steps))
            
            cumulative_time = 0
            for i, step in enumerate(steps):
                cumulative_time += step.get("latency_ms", 500)
                
                # Detect concepts
                concepts = self._extract_concepts(step.get("content", ""))
                numbers = re.findall(r"\d+\.?\d*", step.get("content", ""))[:5]
                
                # Classify activation
                atype = self._classify_activation(step.get("content", ""))
                
                # Strength = how many concepts/numbers + confidence
                strength = min(1.0, len(concepts) * 0.2 + len(numbers) * 0.15 + 0.3)
                confidence = self._estimate_confidence(step.get("content", ""))
                
                voxel = Voxel(
                    voxel_id=f"{scan.scan_id}_{mk}_{i}",
                    model=mk,
                    step_index=i,
                    activation_type=atype,
                    concepts=concepts,
                    numbers=numbers,
                    strength=strength,
                    confidence=confidence,
                    content=step.get("content", "")[:200],
                    time_ms=cumulative_time,
                )
                all_voxels.append(voxel)
        
        am.n_voxels = len(all_voxels)
        am.total_activation = sum(v.strength for v in all_voxels)
        am.peak_activation = max((v.strength for v in all_voxels), default=0)
        
        # 2. Build slices (one per step depth across all models)
        for step_idx in range(max_steps):
            slice_voxels = [v for v in all_voxels if v.step_index == step_idx]
            
            # Agreement at this slice
            answers_at_slice = []
            for v in slice_voxels:
                if v.numbers:
                    answers_at_slice.append(v.numbers[-1])
            agreement = len(set(answers_at_slice)) == 1 if answers_at_slice else False
            
            # Hot/cold concepts at this slice
            concept_counts = Counter(c for v in slice_voxels for c in v.concepts)
            hot = [c for c, n in concept_counts.most_common(5) if n >= 2]
            cold = [c for c, n in concept_counts.items() if n == 1]
            
            cslice = CognitiveSlice(
                slice_index=step_idx,
                question=scan.question[:60],
                voxels=slice_voxels,
                agreement=1.0 if agreement else 0.0,
                hot_concepts=hot,
                cold_concepts=cold,
            )
            am.slices.append(cslice)
        
        # 3. Hot spots (concepts that activate across multiple models)
        concept_activation = defaultdict(list)
        for v in all_voxels:
            for c in v.concepts:
                concept_activation[c].append(v.model)
        
        am.hot_spots = {
            c: len(set(models)) / scan.n_models
            for c, models in concept_activation.items()
            if len(set(models)) >= 2
        }
        
        # 4. Cold spots (expected concepts that didn't activate)
        expected_concepts = self._extract_concepts(scan.question)
        activated_concepts = set(c for v in all_voxels for c in v.concepts)
        am.cold_spots = [c for c in expected_concepts if c not in activated_concepts]
        
        # 5. Deactivations (concepts mentioned then dropped)
        concept_first = {}
        concept_last = {}
        for v in sorted(all_voxels, key=lambda v: v.step_index):
            for c in v.concepts:
                if c not in concept_first: concept_first[c] = v.step_index
                concept_last[c] = v.step_index
        
        for c in concept_first:
            span = concept_last[c] - concept_first[c]
            if span == 0 and concept_first[c] < max_steps - 1:
                am.deactivations.append({
                    "concept": c,
                    "first_seen": concept_first[c],
                    "last_seen": concept_last[c],
                    "span": span,
                    "note": f"'{c}' appeared at step {concept_first[c]} then vanished — suppressed",
                })
        
        # 6. Connectivity (concepts that co-activate in same voxel)
        pair_counts = Counter()
        for v in all_voxels:
            for i, c1 in enumerate(v.concepts):
                for c2 in v.concepts[i+1:]:
                    pair = tuple(sorted([c1, c2]))
                    pair_counts[pair] += 1
        
        for (c1, c2), count in pair_counts.most_common(20):
            if count >= 2:
                am.connectivity.setdefault(c1, []).append(c2)
                am.connectivity.setdefault(c2, []).append(c1)
        
        # 7. Temporal profile (activation over time)
        if all_voxels:
            time_bins = defaultdict(list)
            for v in all_voxels:
                bucket = int(v.time_ms / 1000)  # 1-second bins
                time_bins[bucket].append(v)
            
            for bucket in sorted(time_bins.keys()):
                voxels = time_bins[bucket]
                avg_strength = statistics.mean(v.strength for v in voxels)
                avg_confidence = statistics.mean(v.confidence for v in voxels)
                models_active = len(set(v.model for v in voxels))
                
                am.temporal_profile.append({
                    "time_s": bucket,
                    "n_voxels": len(voxels),
                    "avg_strength": round(avg_strength, 2),
                    "avg_confidence": round(avg_confidence, 2),
                    "models_active": models_active,
                    "activation_types": list(set(v.activation_type.value for v in voxels)),
                })
        
        # 8. Cross-model registration (shared cognitive space)
        for mk, trace in scan.traces.items():
            mk_voxels = [v for v in all_voxels if v.model == mk]
            if mk_voxels:
                am.registration[mk] = {
                    "n_voxels": len(mk_voxels),
                    "avg_strength": round(statistics.mean(v.strength for v in mk_voxels), 2),
                    "avg_confidence": round(statistics.mean(v.confidence for v in mk_voxels), 2),
                    "concepts": list(set(c for v in mk_voxels for c in v.concepts))[:10],
                    "activation_types": list(set(v.activation_type.value for v in mk_voxels)),
                    "correct": trace.get("correct", False),
                }
        
        # 9. Spline: interpolate the topology between slices
        am.spline_points = self._spline(am.slices, am.temporal_profile)
        
        return am
    
    # ─── SPLINE RECONSTRUCTION ─────────────────────────────────────────────
    
    def _spline(self, slices: List[CognitiveSlice], 
                temporal: List[Dict]) -> List[Dict]:
        """Interpolate the continuous topology from discrete slices.
        
        This is the key insight from Casey's fMRI analogy:
        The slices are discrete samples. The spline reconstructs
        the continuous topology BETWEEN slices — the shape that
        exists in the dimension the slices don't directly measure.
        
        In fMRI: blood flow samples → neural activity reconstruction
        Here: trace samples → cognitive topology reconstruction
        """
        if len(slices) < 2:
            return []
        
        points = []
        for i in range(len(slices) - 1):
            s0 = slices[i]
            s1 = slices[i + 1]
            
            # Interpolate between slices
            n_hot_0 = len(s0.hot_concepts)
            n_hot_1 = len(s1.hot_concepts)
            n_cold_0 = len(s0.cold_concepts)
            n_cold_1 = len(s1.cold_concepts)
            agree_0 = s0.agreement
            agree_1 = s1.agreement
            
            # Midpoint values (the "inter-slice reality")
            mid_hot = (n_hot_0 + n_hot_1) / 2
            mid_cold = (n_cold_0 + n_cold_1) / 2
            mid_agree = (agree_0 + agree_1) / 2
            
            # Derivative (rate of change)
            d_hot = n_hot_1 - n_hot_0
            d_agree = agree_1 - agree_0
            
            points.append({
                "from_slice": i,
                "to_slice": i + 1,
                "mid_hot_concepts": mid_hot,
                "mid_cold_concepts": mid_cold,
                "mid_agreement": mid_agree,
                "d_hot": d_hot,
                "d_agreement": d_agree,
                "phase": "converging" if d_agree > 0 else "diverging" if d_agree < 0 else "stable",
                "activation_velocity": d_hot,
            })
        
        return points
    
    # ─── REPORTING ─────────────────────────────────────────────────────────
    
    def report(self, scan: ScanResult) -> str:
        """Human-readable fMRI report."""
        am = scan.activation_map
        if not am: return "No activation map."
        
        lines = [
            f"{'='*60}",
            f"FUNCTIONAL IMAGING REPORT",
            f"{'='*60}",
            f"Question: {am.question[:70]}",
            f"Expected: {am.expected}",
            f"Models: {scan.n_models} | Correct: {scan.n_correct}/{scan.n_models}",
            f"Voxels: {am.n_voxels} | Peak activation: {am.peak_activation:.2f}",
            "",
        ]
        
        # Hot spots
        if am.hot_spots:
            lines.append("HOT SPOTS (multi-model activation):")
            for concept, strength in sorted(am.hot_spots.items(), key=lambda x: -x[1])[:10]:
                bar = "█" * int(strength * 20)
                lines.append(f"  🔴 {concept:20s} {bar} {strength:.0%}")
        
        # Cold spots
        if am.cold_spots:
            lines.append(f"\nCOLD SPOTS (unactivated):")
            for c in am.cold_spots[:10]:
                lines.append(f"  🔵 {c}")
        
        # Deactivations
        if am.deactivations:
            lines.append(f"\nDEACTIVATIONS (suppressed concepts):")
            for d in am.deactivations[:5]:
                lines.append(f"  ⚫ {d['note']}")
        
        # Connectivity
        if am.connectivity:
            lines.append(f"\nCONNECTIVITY (co-activation):")
            for c, peers in list(am.connectivity.items())[:8]:
                lines.append(f"  {c} ↔ {', '.join(peers[:4])}")
        
        # Temporal profile
        if am.temporal_profile:
            lines.append(f"\nTEMPORAL PROFILE:")
            for tp in am.temporal_profile[:10]:
                bar = "▓" * int(tp["avg_strength"] * 15)
                lines.append(f"  t={tp['time_s']:2d}s: {bar} strength={tp['avg_strength']:.2f} "
                            f"conf={tp['avg_confidence']:.2f} models={tp['models_active']} "
                            f"types={','.join(tp['activation_types'][:3])}")
        
        # Spline
        if am.spline_points:
            lines.append(f"\nSPLINE (inter-slice topology):")
            for sp in am.spline_points:
                lines.append(f"  slice {sp['from_slice']}→{sp['to_slice']}: "
                            f"phase={sp['phase']} "
                            f"agreement_Δ={sp['d_agreement']:+.1f} "
                            f"activation_vel={sp['d_hot']:+d}")
        
        # Per-model registration
        lines.append(f"\nMODEL REGISTRATION:")
        for mk, reg in am.registration.items():
            sym = "✓" if reg["correct"] else "✗"
            concepts_str = ", ".join(reg["concepts"][:4]) if reg["concepts"] else "-"
            lines.append(f"  {sym} {mk:12s}: strength={reg['avg_strength']:.2f} "
                        f"conf={reg['avg_confidence']:.2f} "
                        f"concepts=[{concepts_str}]")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    def study_report(self, study: StudyResult) -> str:
        """Aggregate study report."""
        lines = [
            f"{'='*60}",
            f"FUNCTIONAL IMAGING STUDY",
            f"{'='*60}",
            f"Study: {study.study_id}",
            f"Questions: {study.n_questions}",
            f"",
        ]
        
        # Aggregate hot spots
        if study.aggregate_hot_spots:
            lines.append("AGGREGATE HOT SPOTS:")
            for c, s in sorted(study.aggregate_hot_spots.items(), key=lambda x: -x[1])[:15]:
                bar = "█" * int(s * 20)
                lines.append(f"  🔴 {c:20s} {bar} {s:.0%}")
        
        # Model profiles
        lines.append(f"\nMODEL PROFILES:")
        for mk, profile in study.model_profiles.items():
            lines.append(f"  {mk:12s}: accuracy={profile['accuracy']:.0%} "
                        f"avg_strength={profile['avg_strength']:.2f} "
                        f"avg_confidence={profile['avg_confidence']:.2f} "
                        f"dominant_types={profile.get('dominant_types', [])}")
        
        # Cross-question connectivity
        if study.cross_question_connectivity:
            lines.append(f"\nCROSS-QUESTION CONNECTIVITY:")
            for c, peers in list(study.cross_question_connectivity.items())[:10]:
                lines.append(f"  {c} ↔ {', '.join(peers[:4])}")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    # ─── Internal ──────────────────────────────────────────────────────────
    
    def _parse_steps(self, text: str, is_thinking: bool) -> List[Dict]:
        if not text: return []
        if is_thinking and len(text) > 100:
            chunks = re.split(r"\n\n+", text)
        else:
            chunks = re.split(r"(?<=[.!?])\s+", text)
        
        steps = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            steps.append({"index": i, "content": chunk.strip()[:300]})
        return steps
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract cognitive concepts from text."""
        concepts = []
        # Mathematical operations
        if re.search(r"(?i)(?:multipl|product|\*|\×)", text): concepts.append("multiplication")
        if re.search(r"(?i)(?:add|sum|\+)", text): concepts.append("addition")
        if re.search(r"(?i)(?:subtract|minus|−|-)", text): concepts.append("subtraction")
        if re.search(r"(?i)(?:square|²|\^2)", text): concepts.append("squaring")
        if re.search(r"(?i)(?:cub|³|\^3)", text): concepts.append("cubing")
        if re.search(r"(?i)(?:divid|quotient|÷|/)", text): concepts.append("division")
        # Reasoning operations
        if re.search(r"(?i)(?:substit|replace|plug in)", text): concepts.append("substitution")
        if re.search(r"(?i)(?:verif|check|confirm)", text): concepts.append("verification")
        if re.search(r"(?i)(?:simplif|reduce|factor)", text): concepts.append("simplification")
        if re.search(r"(?i)(?:pattern|sequence|next)", text): concepts.append("pattern_recognition")
        if re.search(r"(?i)(?:pressure|force|hydraulic|PSI|bore)", text): concepts.append("hydraulic_reasoning")
        if re.search(r"(?i)(?:compute|calcul|evaluat)", text): concepts.append("computation")
        if re.search(r"(?i)(?:step|first|then|next)", text): concepts.append("sequencing")
        if re.search(r"(?i)(?:formula|express|equation)", text): concepts.append("formula_application")
        if re.search(r"(?i)(?:result|answer|output)", text): concepts.append("result_production")
        return concepts
    
    def _classify_activation(self, text: str) -> ActivationType:
        scores = {
            ActivationType.COMPUTE: len(re.findall(r"(?i)(?:comput|calcul|=|result|equals|gives)", text)),
            ActivationType.VERIFY: len(re.findall(r"(?i)(?:check|verif|confirm|make sure)", text)),
            ActivationType.EXPLORE: len(re.findall(r"(?i)(?:alternati|or maybe|could also|different)", text)),
            ActivationType.REJECT: len(re.findall(r"(?i)(?:wrong|incorrect|not right|no,|but that)", text)),
            ActivationType.CONFUSE: len(re.findall(r"(?i)(?:hmm|wait|not sure|uncertain|let me think)", text)),
            ActivationType.CORRECT: len(re.findall(r"(?i)(?:actually|correction|I was wrong|mistake)", text)),
            ActivationType.METACOGNITIVE: len(re.findall(r"(?i)(?:I need to|approach|strategy|let me)", text)),
        }
        if not scores or max(scores.values()) == 0:
            return ActivationType.COMPUTE
        return max(scores, key=scores.get)
    
    def _estimate_confidence(self, text: str) -> float:
        h = len(re.findall(r"(?i)(?:definitely|certain|clearly|obviously|exactly)", text))
        l = len(re.findall(r"(?i)(?:maybe|perhaps|might|not sure|uncertain|hmm|wait)", text))
        if h > l: return min(0.95, 0.7 + h * 0.1)
        if l > h: return max(0.2, 0.6 - l * 0.1)
        return 0.7
    
    def _aggregate_activation(self, scans):
        hot = defaultdict(float)
        cold = []
        n = len(scans)
        for scan in scans:
            am = scan.activation_map
            if not am: continue
            for c, s in am.hot_spots.items():
                hot[c] += s / n
        
        # Cold = concepts expected but never hot
        for scan in scans:
            if scan.activation_map:
                cold.extend(scan.activation_map.cold_spots)
        
        return dict(sorted(hot.items(), key=lambda x: -x[1])[:20]), list(set(cold))
    
    def _build_model_profiles(self, scans):
        profiles = defaultdict(lambda: {"correct": 0, "total": 0, "strengths": [], "confidences": [], "types": Counter()})
        for scan in scans:
            am = scan.activation_map
            if not am: continue
            for mk, reg in am.registration.items():
                profiles[mk]["total"] += 1
                if reg["correct"]: profiles[mk]["correct"] += 1
                profiles[mk]["strengths"].append(reg["avg_strength"])
                profiles[mk]["confidences"].append(reg["avg_confidence"])
                for t in reg["activation_types"]:
                    profiles[mk]["types"][t] += 1
        
        result = {}
        for mk, p in profiles.items():
            result[mk] = {
                "accuracy": p["correct"] / p["total"] if p["total"] else 0,
                "avg_strength": statistics.mean(p["strengths"]) if p["strengths"] else 0,
                "avg_confidence": statistics.mean(p["confidences"]) if p["confidences"] else 0,
                "dominant_types": [t for t, _ in p["types"].most_common(3)],
            }
        return result
    
    def _cross_question_connectivity(self, scans):
        """Find concepts that co-activate ACROSS different questions."""
        pair_counts = Counter()
        for scan in scans:
            am = scan.activation_map
            if not am: continue
            concepts = list(am.hot_spots.keys())
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i+1:]:
                    pair = tuple(sorted([c1, c2]))
                    pair_counts[pair] += 1
        
        connectivity = defaultdict(list)
        for (c1, c2), count in pair_counts.most_common(15):
            if count >= 2:
                connectivity[c1].append(c2)
                connectivity[c2].append(c1)
        return dict(connectivity)
    
    # ─── Export ─────────────────────────────────────────────────────────────
    
    def export_scan(self, scan: ScanResult, path: str):
        with open(path, "w") as f:
            json.dump(asdict(scan), f, indent=2, default=str)
    
    def export_study(self, study: StudyResult, path: str):
        with open(path, "w") as f:
            json.dump(asdict(study), f, indent=2, default=str)


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="Functional Imaging — fMRI for model cognition")
    p.add_argument("question", nargs="?", default="a*a - a*b + b*b where a=5, b=3")
    p.add_argument("--expected", default=None)
    p.add_argument("--study", help="JSON file with [{question, expected}]")
    p.add_argument("--output", default=None)
    p.add_argument("--models", nargs="+", default=None)
    args = p.parse_args()
    
    fi = FunctionalImager()
    
    if args.study:
        with open(args.study) as f:
            questions = json.load(f)
        q_list = [(q["question"], q.get("expected")) for q in questions]
        study = fi.study(q_list, models=args.models)
        print(fi.study_report(study))
        if args.output:
            fi.export_study(study, args.output)
            print(f"\nSaved to {args.output}")
    else:
        scan = fi.scan(args.question, expected=args.expected, models=args.models)
        print(fi.report(scan))
        if args.output:
            fi.export_scan(scan, args.output)
            print(f"\nSaved to {args.output}")

if __name__ == "__main__":
    main()
