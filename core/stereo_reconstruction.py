#!/usr/bin/env python3
"""core/stereo_reconstruction.py — Poly-Resonant Stereo Reconstruction

THE INSIGHT (Casey's analogy, extended):

  Mono imaging   = one receiver. You get signal strength. That's it.
  Stereo imaging = two receivers. You don't "compare signals."
                    You RECONSTRUCT the 3D space from:
                    - Inter-arrival time (delay = distance)
                    - Phase differential (modulation = material properties)
                    - Amplitude diff (attenuation = geometry)
                    - Resonance patterns (poly-resonance = structure)
                    
  The stereo image isn't "what left and right heard."
  The stereo image is the RECONSTRUCTION of what PRODUCED those hearings.
  The diffs ARE the geometry. The reconstruction IS the physics.

APPLIED TO MODEL COGNITION:

  One model query  = mono. You get an answer. Signal strength.
  Two model queries ≠ "compare answers." That's just stereo summing.
  
  True stereo reconstruction = reconstruct the COGNITIVE SPACE
  that produced both answers, using:
  
    - Response delay (latency = processing depth)
    - Confidence differential (modulation = certainty topology)
    - Trace divergence (phase = where models' cognition splits)
    - Co-activation patterns (resonance = shared structure)
    - Deactivation diff (suppression = what each model ignored)
    
  The reconstruction IS the space. The models are just receivers.

THE PHYSICS:

  Sound in air:
    delay = distance / speed_of_sound
    phase_diff = delay × frequency
    attenuation = 1 / distance²
    resonance = natural_frequency × material_geometry
    
  Models in cognition space:
    delay = latency_ms (processing depth)
    phase = step ordering (where models diverge in their trace)
    attenuation = confidence decay (how certainty drops with depth)
    resonance = concept co-activation (what activates together)
    
  The stereo reconstruction:
    Given two (or N) model responses to the same prompt,
    reconstruct the PROBLEM SPACE that produced both responses.
    
  This is NOT consensus (majority vote).
  This is NOT averaging (mean of answers).
  This is RECONSTRUCTION (inverse problem: what space produces these signals?).

THE MATH:

  In acoustic stereo, cross-correlation of L and R channels produces
  a depth map. The peaks in the cross-correlation function correspond
  to the spatial location of sound sources.
  
  In model stereo, cross-correlation of traces produces a DEPTH MAP
  of the problem space. Peaks correspond to cognitive "surfaces" —
  the stable structure of the problem that all models "bounce off."
  
  The correlation function:
    C(t) = Σ model_A.trace[i] × model_B.trace[i+t]
    
  Peaks in C(t) = stable cognitive surfaces (true structure)
  Valleys in C(t) = interference nulls (model-specific artifacts)
  
  The INTERFERENCE PATTERN IS THE DATA.
  Not the individual signals. The INTERFERENCE.

Usage:
    from core.stereo_reconstruction import StereoReconstructor
    
    sr = StereoReconstructor()
    
    # Two-model stereo
    image = sr.reconstruct("a*a - a*b + b*b where a=5, b=3", expected="19")
    
    # Multi-model array (like a phased array)
    image = sr.phased_array(question, n_models=6)
    
    # Full reconstruction with depth map
    depth_map = sr.depth_map(image)
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
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or "").strip()
        return {
            "content": content,
            "reasoning_content": reasoning,
            "latency_ms": lat,
            "tokens": d.get("usage", {}).get("total_tokens", 0),
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}

def _extract_num(text):
    if not text: return None
    nums = re.findall(r"-?\d+\.?\d*", text)
    return nums[-1] if nums else None


RECEIVER_MODELS = {
    "seed-mini":   {"id": "ByteDance/Seed-2.0-mini",     "system": "You are a calculator. Output the result number ONLY.", "mt": 80},
    "gemini-lite":  {"id": "google/gemini-3.1-flash-lite", "system": "You are a calculator. Output the result number ONLY.", "mt": 80},
    "hermes-70b":   {"id": "NousResearch/Hermes-3-Llama-3.1-70B", "system": "Output ONLY the number.", "mt": 80},
    "qwen2.5-72b":  {"id": "Qwen/Qwen2.5-72B-Instruct",   "system": "Output ONLY the number.", "mt": 80},
    "qwen-4b":     {"id": "Qwen/Qwen3.5-4B",              "system": "", "mt": 500, "thinking": True},
}


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Waveform:
    """A model's response treated as a waveform.
    
    In acoustics: amplitude over time.
    In cognition: confidence × activation over reasoning steps.
    
    The waveform IS the signal. The stereo reconstruction 
    operates on pairs of waveforms.
    """
    model: str
    answer: Optional[str]
    correct: bool
    # The "amplitude" — confidence at each reasoning step
    amplitude: List[float] = field(default_factory=list)
    # The "frequency" — how many concepts activate per step
    frequency: List[float] = field(default_factory=list)
    # The "phase" — the ordering of concepts activated
    phase: List[str] = field(default_factory=list)  # concepts in order
    # Latency = inter-arrival time (processing depth)
    delay_ms: float = 0
    # Total energy (sum of amplitudes)
    energy: float = 0
    # Peak amplitude
    peak: float = 0
    # Raw text
    raw_content: str = ""
    raw_reasoning: str = ""

@dataclass
class InterferencePoint:
    """A point in the interference pattern between two waveforms.
    
    Where two waves constructively interfere = cognitive surface (stable structure)
    Where two waves destructively interfere = interference null (model artifact)
    """
    concept: str
    # Constructive interference strength (-1 to 1)
    correlation: float = 0
    # Time delay between models reaching this concept
    phase_delay: int = 0
    # Is this constructive (same direction) or destructive (opposite)?
    constructive: bool = True
    # Confidence diff (modulation)
    confidence_diff: float = 0

@dataclass
class DepthPoint:
    """A point in the reconstructed depth map.
    
    Like a point in a stereo depth map (distance from camera),
    this represents how "deep" a concept is in the problem space —
    how far from the surface (obvious) to the core (structural).
    """
    concept: str
    depth: float  # 0 = surface (all models agree), 1 = deep (contested)
    certainty: float  # How certain we are about this depth measurement
    # Which models "see" this concept and which don't
    visible_to: List[str] = field(default_factory=list)
    occluded_from: List[str] = field(default_factory=list)

@dataclass
class StereoImage:
    """The reconstructed 3D cognitive space.
    
    This IS the stereo image — not the sum of two signals,
    but the RECONSTRUCTION of the space that produced them.
    
    Just as a stereo photograph reconstructs 3D from 2D parallax,
    this reconstructs the problem topology from model divergences.
    """
    image_id: str
    question: str
    expected: Optional[str]
    
    # The waveforms (one per model/receiver)
    waveforms: Dict[str, Waveform] = field(default_factory=dict)
    
    # The interference pattern (pairwise cross-correlations)
    interference: List[InterferencePoint] = field(default_factory=list)
    
    # The depth map (reconstructed topology)
    depth_map: List[DepthPoint] = field(default_factory=list)
    
    # Poly-resonance: concepts that resonate across ALL models
    poly_resonances: List[Dict] = field(default_factory=list)
    
    # Surfaces: stable structures (constructive interference peaks)
    surfaces: List[Dict] = field(default_factory=list)
    
    # Nulls: model-specific artifacts (destructive interference)
    nulls: List[Dict] = field(default_factory=list)
    
    # The modulation envelope: how confidence varies across the space
    modulation_envelope: List[Dict] = field(default_factory=list)
    
    # Reconstruction quality
    n_receivers: int = 0
    n_correct: int = 0
    reconstruction_confidence: float = 0
    # How much of the space did we reconstruct?
    coverage: float = 0


# ─── The Stereo Reconstructor ─────────────────────────────────────────────────

class StereoReconstructor:
    """Reconstruct cognitive space from model interference patterns.
    
    The key insight: don't compare answers. Reconstruct the SPACE
    that produced them. The diffs ARE the geometry.
    """
    
    def __init__(self, models: Dict = None, api_key: str = None):
        self.models = models or RECEIVER_MODELS
        self.api_key = api_key
    
    # ─── RECEIVE (capture waveforms) ───────────────────────────────────────
    
    def _receive(self, question: str, models: List[str] = None) -> Dict[str, Waveform]:
        """Capture waveforms from all receivers (models)."""
        waveforms = {}
        
        for mk in (models or list(self.models.keys())):
            if mk not in self.models: continue
            mi = self.models[mk]
            
            resp = _query(mi["id"], question, system=mi.get("system", ""),
                         max_tokens=mi.get("mt", 80), api_key=self.api_key)
            
            if "error" in resp:
                waveforms[mk] = Waveform(model=mk, answer=None, correct=False, delay_ms=resp.get("latency_ms", 0))
                continue
            
            content = resp.get("content", "")
            reasoning = resp.get("reasoning_content", "")
            text = content if content else reasoning
            answer = _extract_num(content) or _extract_num(reasoning)
            
            # Parse the waveform
            steps = self._parse_steps(text)
            
            # Amplitude: confidence at each step
            amplitudes = [self._step_confidence(s) for s in steps]
            
            # Frequency: concepts per step
            frequencies = [len(self._extract_concepts(s)) for s in steps]
            
            # Phase: concepts in activation order
            phase = []
            for s in steps:
                phase.extend(self._extract_concepts(s))
            
            energy = sum(amplitudes) if amplitudes else 0
            peak = max(amplitudes) if amplitudes else 0
            
            waveforms[mk] = Waveform(
                model=mk, answer=answer, correct=False,
                amplitude=amplitudes, frequency=frequencies, phase=phase,
                delay_ms=resp.get("latency_ms", 0),
                energy=energy, peak=peak,
                raw_content=content[:500],
                raw_reasoning=reasoning[:1000],
            )
        
        return waveforms
    
    # ─── RECONSTRUCT (the core operation) ───────────────────────────────────
    
    def reconstruct(self, question: str, expected: str = None,
                    models: List[str] = None) -> StereoImage:
        """Reconstruct the cognitive space from model interference.
        
        1. RECEIVE: Capture waveforms from all models
        2. CROSS-CORRELATE: Find interference patterns between all pairs
        3. DEPTH MAP: Compute depth from delay + correlation
        4. POLY-RESONANCE: Find concepts resonating across all models
        5. SURFACE EXTRACTION: Identify stable structures
        6. NULL DETECTION: Identify model-specific artifacts
        7. MODULATION: Map confidence envelope across the space
        """
        waveforms = self._receive(question, models=models)
        
        # Mark correct
        n_correct = 0
        for mk, wf in waveforms.items():
            if expected and wf.answer:
                try:
                    wf.correct = abs(float(wf.answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                except:
                    pass
                if wf.correct: n_correct += 1
        
        image = StereoImage(
            image_id=str(uuid.uuid4())[:8],
            question=question,
            expected=expected,
            waveforms=waveforms,
            n_receivers=len(waveforms),
            n_correct=n_correct,
        )
        
        # 2. Cross-correlation: pairwise interference
        model_keys = list(waveforms.keys())
        all_interference = []
        
        for i in range(len(model_keys)):
            for j in range(i + 1, len(model_keys)):
                interference = self._cross_correlate(
                    waveforms[model_keys[i]], waveforms[model_keys[j]]
                )
                all_interference.extend(interference)
        
        # Deduplicate and aggregate interference
        image.interference = self._aggregate_interference(all_interference)
        
        # 3. Depth map
        image.depth_map = self._compute_depth_map(waveforms, image.interference)
        
        # 4. Poly-resonance (concepts resonating across ALL models)
        image.poly_resonances = self._find_poly_resonances(waveforms)
        
        # 5. Surfaces (stable structures)
        image.surfaces = self._extract_surfaces(image.interference, waveforms)
        
        # 6. Nulls (model-specific artifacts)
        image.nulls = self._find_nulls(waveforms)
        
        # 7. Modulation envelope
        image.modulation_envelope = self._compute_modulation(waveforms)
        
        # Reconstruction quality
        n_concepts = len(set(c for wf in waveforms.values() for c in wf.phase))
        n_surfaces = len(image.surfaces)
        image.coverage = n_surfaces / max(n_concepts, 1)
        image.reconstruction_confidence = min(1.0, 
            n_correct / max(len(waveforms), 1) * 0.4 + 
            n_surfaces * 0.1 +
            len(image.poly_resonances) * 0.1)
        
        return image
    
    # ─── CROSS-CORRELATION ─────────────────────────────────────────────────
    
    def _cross_correlate(self, wf_a: Waveform, wf_b: Waveform) -> List[InterferencePoint]:
        """Cross-correlate two model waveforms.
        
        This is the CORE of stereo reconstruction.
        Not "compare answers" but "find the interference pattern."
        
        For each concept in either model's trace:
          - correlation = do both models activate this concept? (+1 if yes, -1 if no)
          - phase_delay = how many steps apart did they reach this concept?
          - confidence_diff = how different are their confidences when activating?
          
        Constructive interference (both activate, same phase) = surface
        Destructive interference (one activates, one suppresses) = null
        """
        interference = []
        
        # All concepts from both models
        concepts_a = {c: i for i, c in enumerate(wf_a.phase)}
        concepts_b = {c: i for i, c in enumerate(wf_b.phase)}
        all_concepts = set(concepts_a.keys()) | set(concepts_b.keys())
        
        for concept in all_concepts:
            in_a = concept in concepts_a
            in_b = concept in concepts_b
            
            if in_a and in_b:
                # Both activate this concept — constructive
                correlation = 1.0
                phase_delay = abs(concepts_a[concept] - concepts_b[concept])
                conf_a = wf_a.amplitude[concepts_a[concept]] if concepts_a[concept] < len(wf_a.amplitude) else 0.7
                conf_b = wf_b.amplitude[concepts_b[concept]] if concepts_b[concept] < len(wf_b.amplitude) else 0.7
                confidence_diff = abs(conf_a - conf_b)
                constructive = True
            elif in_a or in_b:
                # Only one activates — partial interference
                correlation = -0.5
                phase_delay = 0
                confidence_diff = 0.3
                constructive = False
            
            interference.append(InterferencePoint(
                concept=concept,
                correlation=correlation,
                phase_delay=phase_delay,
                constructive=constructive,
                confidence_diff=confidence_diff,
            ))
        
        return interference
    
    def _aggregate_interference(self, points: List[InterferencePoint]) -> List[InterferencePoint]:
        """Aggregate interference points across all pairs."""
        concept_data = defaultdict(lambda: {"correlations": [], "delays": [], "confs": [], "constructive": 0, "destructive": 0})
        
        for p in points:
            d = concept_data[p.concept]
            d["correlations"].append(p.correlation)
            d["delays"].append(p.phase_delay)
            d["confs"].append(p.confidence_diff)
            if p.constructive: d["constructive"] += 1
            else: d["destructive"] += 1
        
        aggregated = []
        for concept, d in concept_data.items():
            avg_corr = statistics.mean(d["correlations"]) if d["correlations"] else 0
            avg_delay = statistics.mean(d["delays"]) if d["delays"] else 0
            avg_conf = statistics.mean(d["confs"]) if d["confs"] else 0
            constructive = d["constructive"] > d["destructive"]
            
            aggregated.append(InterferencePoint(
                concept=concept,
                correlation=round(avg_corr, 2),
                phase_delay=round(avg_delay, 1),
                constructive=constructive,
                confidence_diff=round(avg_conf, 2),
            ))
        
        return sorted(aggregated, key=lambda p: -p.correlation)
    
    # ─── DEPTH MAP ─────────────────────────────────────────────────────────
    
    def _compute_depth_map(self, waveforms: Dict[str, Waveform],
                           interference: List[InterferencePoint]) -> List[DepthPoint]:
        """Compute depth map from interference patterns.
        
        Depth = how contested / uncertain a concept is.
        Surface (0) = all models agree, high correlation
        Deep (1) = models disagree, high interference
        """
        depth_points = []
        
        for ip in interference:
            # Depth from correlation (inverse)
            # High correlation = surface (0), Low/negative = deep (1)
            depth = (1 - ip.correlation) / 2  # Map [-1,1] → [1,0]
            depth = max(0, min(1, depth))
            
            # Certainty from number of data points
            certainty = min(1.0, abs(ip.correlation))
            
            # Which models see this concept
            visible = [mk for mk, wf in waveforms.items() if ip.concept in wf.phase]
            occluded = [mk for mk, wf in waveforms.items() if ip.concept not in wf.phase]
            
            depth_points.append(DepthPoint(
                concept=ip.concept,
                depth=round(depth, 2),
                certainty=round(certainty, 2),
                visible_to=visible,
                occluded_from=occluded,
            ))
        
        return sorted(depth_points, key=lambda dp: dp.depth)
    
    # ─── POLY-RESONANCE ────────────────────────────────────────────────────
    
    def _find_poly_resonances(self, waveforms: Dict[str, Waveform]) -> List[Dict]:
        """Find concepts that resonate across ALL models.
        
        Poly-resonance = a concept that appears in every model's trace,
        regardless of whether they got the answer right.
        
        These are the STRUCTURAL elements of the problem space —
        the surfaces that every cognitive "wave" bounces off.
        
        Like a resonant frequency in physics — every wave excites it.
        """
        if not waveforms: return []
        
        model_keys = list(waveforms.keys())
        concept_sets = [set(wf.phase) for wf in waveforms.values()]
        
        # Intersection: concepts in ALL models
        universal = set.intersection(*concept_sets) if concept_sets else set()
        
        resonances = []
        for concept in universal:
            # Measure resonance strength: how consistently ordered
            positions = []
            for mk in model_keys:
                wf = waveforms[mk]
                if concept in wf.phase:
                    positions.append(wf.phase.index(concept))
            
            # Low variance in position = strong resonance (ordered consistently)
            pos_variance = statistics.variance(positions) if len(positions) > 1 else 0
            resonance_strength = 1.0 / (1.0 + pos_variance)
            
            resonances.append({
                "concept": concept,
                "resonance_strength": round(resonance_strength, 2),
                "positions": positions,
                "ordering_consistent": pos_variance < 1.0,
            })
        
        return sorted(resonances, key=lambda r: -r["resonance_strength"])
    
    # ─── SURFACE EXTRACTION ────────────────────────────────────────────────
    
    def _extract_surfaces(self, interference: List[InterferencePoint],
                          waveforms: Dict[str, Waveform]) -> List[Dict]:
        """Extract stable cognitive surfaces.
        
        Surfaces are interference peaks — concepts where ALL models
        constructively interfere. These are the load-bearing walls
        of the problem space.
        """
        surfaces = []
        
        for ip in interference:
            if ip.constructive and ip.correlation > 0.5:
                n_visible = len([mk for mk, wf in waveforms.items() if ip.concept in wf.phase])
                surfaces.append({
                    "concept": ip.concept,
                    "correlation": ip.correlation,
                    "n_models": n_visible,
                    "phase_delay": ip.phase_delay,
                    "confidence_spread": ip.confidence_diff,
                    "stability": "stable" if ip.phase_delay == 0 else "phase-shifted",
                })
        
        return sorted(surfaces, key=lambda s: -s["correlation"])
    
    # ─── NULL DETECTION ────────────────────────────────────────────────────
    
    def _find_nulls(self, waveforms: Dict[str, Waveform]) -> List[Dict]:
        """Find interference nulls — model-specific artifacts.
        
        A null is a concept activated by ONE model but suppressed by others.
        This is destructive interference — the concept is a model-specific
        cognitive artifact, not a structural element.
        
        BUT: nulls are also DATA. They tell you what each model's
        unique "acoustic signature" looks like. The null pattern
        IS the model's spice expressed in the interference domain.
        """
        nulls = []
        
        for mk, wf in waveforms.items():
            for concept in wf.phase:
                # Check if other models also have this concept
                others_have = sum(1 for mk2, wf2 in waveforms.items() 
                                  if mk2 != mk and concept in wf2.phase)
                total_others = len(waveforms) - 1
                
                if others_have == 0:
                    # Only this model sees this concept — null
                    nulls.append({
                        "concept": concept,
                        "model": mk,
                        "type": "unique_activation",
                        "note": f"Only {mk} activates '{concept}' — model-specific artifact",
                    })
                elif others_have < total_others / 2:
                    nulls.append({
                        "concept": concept,
                        "model": mk,
                        "type": "minority_activation",
                        "note": f"{mk} is among few that activate '{concept}'",
                    })
        
        return nulls
    
    # ─── MODULATION ENVELOPE ───────────────────────────────────────────────
    
    def _compute_modulation(self, waveforms: Dict[str, Waveform]) -> List[Dict]:
        """Compute the confidence modulation envelope.
        
        In acoustics, the modulation envelope shows how amplitude
        varies across frequency bands. Here, it shows how confidence
        varies across the reasoning depth.
        
        The envelope shape IS the problem's difficulty profile:
          - Flat envelope = uniformly easy (all steps same confidence)
          - Rising envelope = gets easier (learning curve)
          - Falling envelope = gets harder (complexity cliff)
          - Peaked envelope = hardest in the middle (computation peak)
        """
        # Align all waveforms by step
        max_depth = max((len(wf.amplitude) for wf in waveforms.values()), default=0)
        
        envelope = []
        for step in range(max_depth):
            values = []
            active_models = []
            for mk, wf in waveforms.items():
                if step < len(wf.amplitude):
                    values.append(wf.amplitude[step])
                    active_models.append(mk)
            
            if values:
                envelope.append({
                    "step": step,
                    "avg_confidence": round(statistics.mean(values), 2),
                    "variance": round(statistics.variance(values), 3) if len(values) > 1 else 0,
                    "n_models": len(active_models),
                    "models": active_models,
                })
        
        return envelope
    
    # ─── PHASED ARRAY ──────────────────────────────────────────────────────
    
    def phased_array(self, questions: List[Tuple[str, str]],
                     models: List[str] = None) -> Dict:
        """Run a phased array scan — multiple questions, full reconstruction.
        
        Like a phased array radar: sweep across the problem space,
        accumulate reconstructions, build the full 3D topology.
        """
        images = []
        all_surfaces = Counter()
        all_resonances = Counter()
        all_nulls_by_model = defaultdict(Counter)
        
        for i, (q, expected) in enumerate(questions):
            print(f"  Array [{i+1}/{len(questions)}]: {q[:50]}...", flush=True)
            image = self.reconstruct(q, expected=expected, models=models)
            images.append(image)
            
            # Accumulate surfaces
            for s in image.surfaces:
                all_surfaces[s["concept"]] += 1
            
            # Accumulate resonances
            for r in image.poly_resonances:
                all_resonances[r["concept"]] += 1
            
            # Accumulate nulls by model
            for n in image.nulls:
                all_nulls_by_model[n["model"]][n["concept"]] += 1
        
        # The global topology
        global_surfaces = {c: count for c, count in all_surfaces.most_common(15) if count >= 2}
        global_resonances = {c: count for c, count in all_resonances.most_common(10) if count >= 2}
        
        # Model signatures (their unique null patterns across questions)
        model_signatures = {}
        for mk, concepts in all_nulls_by_model.items():
            model_signatures[mk] = {
                "unique_activations": dict(concepts.most_common(10)),
                "n_unique": len(concepts),
            }
        
        return {
            "n_questions": len(questions),
            "n_images": len(images),
            "global_surfaces": global_surfaces,
            "global_resonances": global_resonances,
            "model_signatures": model_signatures,
            "per_question": [{
                "question": img.question[:60],
                "expected": img.expected,
                "n_correct": img.n_correct,
                "n_receivers": img.n_receivers,
                "n_surfaces": len(img.surfaces),
                "n_resonances": len(img.poly_resonances),
                "n_nulls": len(img.nulls),
                "coverage": round(img.coverage, 2),
                "reconstruction_confidence": round(img.reconstruction_confidence, 2),
            } for img in images],
        }
    
    # ─── REPORTING ─────────────────────────────────────────────────────────
    
    def report(self, image: StereoImage) -> str:
        """Full stereo reconstruction report."""
        lines = [
            f"{'='*60}",
            f"STEREO RECONSTRUCTION",
            f"{'='*60}",
            f"Question: {image.question[:70]}",
            f"Expected: {image.expected}",
            f"Receivers: {image.n_receivers} | Correct: {image.n_correct}/{image.n_receivers}",
            f"Reconstruction confidence: {image.reconstruction_confidence:.2f}",
            f"Coverage: {image.coverage:.0%}",
            "",
        ]
        
        # Waveforms (the raw signals)
        lines.append("WAVEFORMS (raw signals):")
        for mk, wf in image.waveforms.items():
            sym = "✓" if wf.correct else "✗"
            amp_bar = "▓" * int(wf.energy * 5) if wf.energy else "░"
            lines.append(f"  {sym} {mk:12s}: answer={wf.answer or 'EMPTY':6s} "
                        f"delay={wf.delay_ms:.0f}ms energy={wf.energy:.1f} {amp_bar}")
            if wf.phase:
                lines.append(f"     phase: {' → '.join(wf.phase[:8])}")
        
        # Poly-resonances
        if image.poly_resonances:
            lines.append(f"\nPOLY-RESONANCES (structural elements):")
            for r in image.poly_resonances[:10]:
                ordering = "ordered" if r["ordering_consistent"] else "phase-shifted"
                bar = "〰" * int(r["resonance_strength"] * 10)
                lines.append(f"  🔔 {r['concept']:20s} {bar} str={r['resonance_strength']:.2f} ({ordering})")
        
        # Surfaces
        if image.surfaces:
            lines.append(f"\nSURFACES (stable cognitive structures):")
            for s in image.surfaces[:10]:
                lines.append(f"  ■ {s['concept']:20s} corr={s['correlation']:.2f} "
                            f"models={s['n_models']} {s['stability']}")
        
        # Depth map
        if image.depth_map:
            lines.append(f"\nDEPTH MAP (problem topology):")
            for dp in image.depth_map[:12]:
                depth_bar = "·" * int(dp.depth * 20) + "●"
                vis = len(dp.visible_to)
                lines.append(f"  {dp.concept:20s} depth={dp.depth:.2f} "
                            f"visible_to={vis}/{image.n_receivers} "
                            f"certainty={dp.certainty:.2f} {depth_bar}")
        
        # Nulls
        if image.nulls:
            lines.append(f"\nNULLS (model-specific artifacts):")
            for n in image.nulls[:8]:
                lines.append(f"  ○ {n['model']:12s}: {n['note'][:60]}")
        
        # Modulation envelope
        if image.modulation_envelope:
            lines.append(f"\nMODULATION ENVELOPE (difficulty profile):")
            shape = self._classify_envelope(image.modulation_envelope)
            lines.append(f"  Shape: {shape}")
            for m in image.modulation_envelope[:8]:
                bar = "▓" * int(m["avg_confidence"] * 15)
                lines.append(f"  step {m['step']}: {bar} conf={m['avg_confidence']:.2f} "
                            f"var={m['variance']:.2f} models={m['n_models']}")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    def phased_report(self, result: Dict) -> str:
        lines = [
            f"{'='*60}",
            f"PHASED ARRAY SCAN",
            f"{'='*60}",
            f"Questions: {result['n_questions']}",
            "",
        ]
        
        lines.append("GLOBAL SURFACES (persistent across all questions):")
        for c, count in sorted(result["global_surfaces"].items(), key=lambda x: -x[1]):
            bar = "■" * count
            lines.append(f"  {c:20s} {bar} ({count} questions)")
        
        lines.append(f"\nGLOBAL RESONANCES (universal structural elements):")
        for c, count in sorted(result["global_resonances"].items(), key=lambda x: -x[1]):
            bar = "🔔" * count
            lines.append(f"  {c:20s} {bar} ({count} questions)")
        
        lines.append(f"\nMODEL SIGNATURES (unique null patterns):")
        for mk, sig in result["model_signatures"].items():
            top = list(sig["unique_activations"].keys())[:5]
            lines.append(f"  {mk:12s}: {sig['n_unique']} unique concepts — {', '.join(top)}")
        
        lines.append(f"\nPER-QUESTION:")
        for pq in result["per_question"]:
            lines.append(f"  {pq['question'][:45]:45s} correct={pq['n_correct']}/{pq['n_receivers']} "
                        f"surfaces={pq['n_surfaces']} resonances={pq['n_resonances']} "
                        f"conf={pq['reconstruction_confidence']:.2f}")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    # ─── Internal ──────────────────────────────────────────────────────────
    
    def _parse_steps(self, text: str) -> List[str]:
        if not text: return []
        chunks = re.split(r"(?<=[:.!?])\s+|\n\n+", text)
        return [c.strip() for c in chunks if c.strip()]
    
    def _step_confidence(self, text: str) -> float:
        h = len(re.findall(r"(?i)(?:definitely|certain|clearly|exactly)", text))
        l = len(re.findall(r"(?i)(?:maybe|perhaps|not sure|uncertain|hmm|wait)", text))
        if h > l: return min(0.95, 0.7 + h * 0.1)
        if l > h: return max(0.2, 0.6 - l * 0.1)
        return 0.7
    
    def _extract_concepts(self, text: str) -> List[str]:
        concepts = []
        if re.search(r"(?i)(?:multipl|product|\*)", text): concepts.append("multiplication")
        if re.search(r"(?i)(?:add|sum|\+)", text): concepts.append("addition")
        if re.search(r"(?i)(?:subtract|minus|−)", text): concepts.append("subtraction")
        if re.search(r"(?i)(?:square|²|\^2)", text): concepts.append("squaring")
        if re.search(r"(?i)(?:substit|plug)", text): concepts.append("substitution")
        if re.search(r"(?i)(?:verif|check)", text): concepts.append("verification")
        if re.search(r"(?i)(?:simplif|factor)", text): concepts.append("simplification")
        if re.search(r"(?i)(?:pattern|sequence)", text): concepts.append("pattern_recognition")
        if re.search(r"(?i)(?:pressure|force|hydraulic)", text): concepts.append("hydraulic")
        if re.search(r"(?i)(?:comput|calcul|eval)", text): concepts.append("computation")
        if re.search(r"(?i)(?:formula|express|equation)", text): concepts.append("formula")
        if re.search(r"(?i)(?:result|answer|output)", text): concepts.append("result")
        return concepts
    
    def _classify_envelope(self, envelope: List[Dict]) -> str:
        if len(envelope) < 2: return "flat (insufficient data)"
        confs = [e["avg_confidence"] for e in envelope]
        if all(c >= confs[0] - 0.05 for c in confs): return "flat (uniformly easy)"
        if confs[-1] > confs[0] + 0.1: return "rising (gets easier)"
        if confs[-1] < confs[0] - 0.1: return "falling (complexity cliff)"
        mid = len(confs) // 2
        if confs[mid] > confs[0] + 0.1 and confs[mid] > confs[-1] + 0.1: return "peaked (hardest in middle)"
        return "undulating (variable difficulty)"


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="Stereo Reconstruction — poly-resonant cognitive imaging")
    p.add_argument("question", nargs="?", default="a*a - a*b + b*b where a=5, b=3")
    p.add_argument("--expected", default=None)
    p.add_argument("--phased", help="JSON file with [{question, expected}]")
    p.add_argument("--output", default=None)
    p.add_argument("--models", nargs="+", default=None)
    args = p.parse_args()
    
    sr = StereoReconstructor()
    
    if args.phased:
        with open(args.phased) as f:
            questions = json.load(f)
        q_list = [(q["question"], q.get("expected")) for q in questions]
        result = sr.phased_array(q_list, models=args.models)
        print(sr.phased_report(result))
    else:
        image = sr.reconstruct(args.question, expected=args.expected, models=args.models)
        print(sr.report(image))
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(asdict(image) if not args.phased else result, f, indent=2, default=str)
        print(f"\nSaved to {args.output}")

if __name__ == "__main__":
    main()
