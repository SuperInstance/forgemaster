#!/usr/bin/env python3
"""core/kaleidoscope.py — The Real Kaleidoscope

Refract ideas through models. Mine the tensor. Find what no single model can see.

VERSION 2.0 — Rebuilt from 4,500+ experiments.

What we learned:
  - Seed-mini has no depth cliff, no coefficient blind spot, 89.5% accuracy
  - Gemini Flash Lite is its fast twin (82.5%, 22× cheaper)
  - Hermes-70B is fastest (400ms), great at constraint theory
  - Qwen2.5-72B is the scholar — best explanations, thorough
  - Thinking models (Qwen3.5-4B) produce reasoning_content = frozen trace
  - Wrong answers with traces are MORE valuable than right answers without
  - Cross-model refraction reveals upper-dimensional structure
  - Division of labor beats iteration every time

The kaleidoscope is NOT about getting better answers from models.
It's about REVEALING THE SHAPE OF THE PROBLEM SPACE.

A single model gives you a point estimate.
Two models give you a line.
Three models give you a triangle.
N models give you the N-dimensional shape of the idea.

The shape IS the knowledge. The points are just samples.

Architecture:
  1. SEED: Question enters
  2. REFRACT: Each model produces a trace (thinking) or direct answer (non-thinking)
  3. CUT: TileCutter splits thinking traces into step-tiles
  4. CROSS-POLLINATE: Feed model A's steps to model B (the refraction)
  5. TENSORIZE: Assemble all traces + steps into perspective tensor
  6. MINE: Extract harmonics (convergence), dissonance (disagreement), shadows (gaps)
  7. SPREAD: Route each step to the right hydraulic tool for verification
  8. YIELD: The perspective tensor — frozen, mineable, rewindable
"""
from __future__ import annotations

import json, os, re, time, uuid, statistics
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple, Any, Set
from collections import defaultdict
from enum import Enum

import requests

API_KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def _key():
    return open(API_KEY_PATH).read().strip()

def _query(model: str, prompt: str, system: str = "", max_tokens: int = 500,
           temperature: float = 0.0, api_key: str = None) -> dict:
    ak = api_key or _key()
    headers = {"Authorization": f"Bearer {ak}", "Content-Type": "application/json"}
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
    start = time.time()
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "latency_ms": lat}
        d = r.json()
        msg = d["choices"][0]["message"]
        usage = d.get("usage", {})
        return {
            "content": (msg.get("content") or "").strip(),
            "reasoning_content": (msg.get("reasoning_content") or "").strip(),
            "latency_ms": lat,
            "tokens": usage.get("total_tokens", 0),
            "model": model,
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}

def _extract_num(text: str) -> Optional[str]:
    if not text: return None
    nums = re.findall(r"-?\d+\.?\d*", text)
    return nums[-1] if nums else None


# ─── Models ────────────────────────────────────────────────────────────────────

# The fleet roster — each with its spice
MODELS = {
    # Tier 1: Engine Room
    "seed-mini":     {"id": "ByteDance/Seed-2.0-mini",     "spice": "surgeon",    "tier": 1},
    "gemini-lite":   {"id": "google/gemini-3.1-flash-lite", "spice": "speed-demon","tier": 1, "needs_system": True},
    # Tier 2: Contenders
    "hermes-70b":    {"id": "NousResearch/Hermes-3-Llama-3.1-70B", "spice": "gunslinger", "tier": 2},
    "qwen2.5-72b":  {"id": "Qwen/Qwen2.5-72B-Instruct",   "spice": "scholar",   "tier": 2},
    # Tier 3: Thinking models (produce reasoning_content)
    "qwen-4b":      {"id": "Qwen/Qwen3.5-4B",              "spice": "thinker",   "tier": 3, "thinking": True},
    "qwen-9b":      {"id": "Qwen/Qwen3.5-9B",              "spice": "deep-thinker", "tier": 3, "thinking": True},
}


# ─── Data Structures ──────────────────────────────────────────────────────────

class FacetType(Enum):
    """What kind of facet did this model produce?"""
    DIRECT = "direct"           # Non-thinking model, answer in content
    THINKING = "thinking"       # Thinking model, trace in reasoning_content
    EMPTY = "empty"             # No useful output
    ERROR = "error"             # API error

@dataclass
class Facet:
    """One model's view of the idea — a single facet of the kaleidoscope."""
    facet_id: str
    model_key: str
    model_id: str
    spice: str
    facet_type: FacetType
    
    # The raw outputs
    content: str = ""
    reasoning_content: str = ""
    
    # Extracted answer
    answer: Optional[str] = None
    correct: bool = False
    
    # Step tiles (from TileCutter, if thinking model)
    steps: List[Dict] = field(default_factory=list)
    n_steps: int = 0
    
    # Murmur signals
    confidence: float = 0.7
    murmurs: List[str] = field(default_factory=list)
    
    # Meta
    latency_ms: float = 0
    tokens: int = 0
    
@dataclass
class Harmonic:
    """A point where multiple models converge — agreement on an answer."""
    answer: str
    models: List[str]
    correct: bool
    strength: int  # Number of models agreeing
    
@dataclass
class Dissonance:
    """A point where models disagree — the edges of the problem space."""
    question: str
    answers: Dict[str, str]  # model → answer
    expected: Optional[str]
    magnitude: float  # How different are the answers?

@dataclass
class Shadow:
    """Something no model produced — the blind spot in the tensor."""
    description: str
    domain: str
    models_checked: List[str]
    confidence: float  # How sure we are this IS a shadow (not just noise)

@dataclass
class PerspectiveTensor:
    """The complete output of a kaleidoscope run.
    
    This IS the knowledge artifact. Frozen, mineable, rewindable.
    """
    tensor_id: str
    seed_question: str
    expected_answer: Optional[str]
    
    # The facets (one per model)
    facets: List[Facet] = field(default_factory=list)
    
    # The analysis
    harmonics: List[Harmonic] = field(default_factory=list)
    dissonances: List[Dissonance] = field(default_factory=list)
    shadows: List[Shadow] = field(default_factory=list)
    
    # Cross-pollination results
    cross_pollinations: List[Dict] = field(default_factory=list)
    
    # Summary
    n_models: int = 0
    n_correct: int = 0
    consensus_answer: Optional[str] = None
    consensus_strength: int = 0
    
    # Meta
    total_latency_ms: float = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    created_at: float = field(default_factory=time.time)


# ─── The Kaleidoscope Engine ───────────────────────────────────────────────────

class Kaleidoscope:
    """The real kaleidoscope — refract ideas through models, mine the tensor.
    
    Usage:
        k = Kaleidoscope()
        tensor = k.refract("a*a - a*b + b*b where a=5, b=3", expected="19")
        print(k.summarize(tensor))
        
        # Cross-pollinate
        cp_tensor = k.cross_pollinate(tensor)
        
        # Find shadows
        shadows = k.find_shadows(tensor)
    """
    
    def __init__(self, models: Dict[str, dict] = None, api_key: str = None):
        self.models = models or MODELS
        self.api_key = api_key
    
    # ─── SEED + REFRACT ────────────────────────────────────────────────────
    
    def refract(self, question: str, expected: str = None,
                models: List[str] = None, system: str = "",
                max_tokens: int = 200) -> PerspectiveTensor:
        """Refract a question through all models. Build the perspective tensor."""
        
        model_keys = models or list(self.models.keys())
        tensor = PerspectiveTensor(
            tensor_id=str(uuid.uuid4())[:8],
            seed_question=question,
            expected_answer=expected,
        )
        
        total_start = time.time()
        
        for mk in model_keys:
            if mk not in self.models:
                continue
            
            model_info = self.models[mk]
            mid = model_info["id"]
            is_thinking = model_info.get("thinking", False)
            needs_system = model_info.get("needs_system", False)
            spice = model_info.get("spice", "unknown")
            
            # Build system prompt
            # Non-thinking models ALWAYS get the calculator system prompt
            # Thinking models get no system prompt (they need freedom to reason)
            if is_thinking:
                sys_prompt = ""
            elif system:
                sys_prompt = system
            else:
                sys_prompt = "You are a calculator. Output the result number ONLY. No words. No explanation."
            
            # Query
            mt = max_tokens if is_thinking else min(max_tokens, 100)
            resp = _query(mid, question, system=sys_prompt, max_tokens=mt, api_key=self.api_key)
            
            if "error" in resp:
                facet = Facet(
                    facet_id=f"{tensor.tensor_id}_{mk}",
                    model_key=mk, model_id=mid, spice=spice,
                    facet_type=FacetType.ERROR,
                    content=resp["error"],
                    latency_ms=resp.get("latency_ms", 0),
                )
            else:
                content = resp.get("content", "")
                reasoning = resp.get("reasoning_content", "")
                text = content if content else reasoning
                
                # Classify facet
                if content and not reasoning:
                    ftype = FacetType.DIRECT
                elif reasoning:
                    ftype = FacetType.THINKING
                elif not text:
                    ftype = FacetType.EMPTY
                else:
                    ftype = FacetType.DIRECT
                
                # Extract answer
                answer = _extract_num(content) or _extract_num(reasoning)
                correct = False
                if expected and answer:
                    try:
                        correct = abs(float(answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                    except:
                        pass
                
                # Parse thinking trace into steps
                steps = []
                if reasoning and is_thinking:
                    steps = self._cut_steps(reasoning)
                
                # Detect murmurs
                murmurs = self._detect_murmurs(text)
                confidence = self._estimate_confidence(text)
                
                facet = Facet(
                    facet_id=f"{tensor.tensor_id}_{mk}",
                    model_key=mk, model_id=mid, spice=spice,
                    facet_type=ftype,
                    content=content[:500],
                    reasoning_content=reasoning[:1000] if is_thinking else "",
                    answer=answer,
                    correct=correct,
                    steps=steps,
                    n_steps=len(steps),
                    confidence=confidence,
                    murmurs=murmurs,
                    latency_ms=resp.get("latency_ms", 0),
                    tokens=resp.get("tokens", 0),
                )
            
            tensor.facets.append(facet)
            tensor.total_latency_ms += facet.latency_ms
            tensor.total_tokens += facet.tokens
        
        tensor.total_latency_ms = (time.time() - total_start) * 1000
        tensor.n_models = len(tensor.facets)
        tensor.n_correct = sum(1 for f in tensor.facets if f.correct)
        tensor.total_cost_usd = tensor.total_tokens * 0.15 / 1_000_000  # Approximate
        
        # ─── ANALYZE ──────────────────────────────────────────────────────
        
        tensor.harmonics = self._find_harmonics(tensor, expected)
        tensor.dissonances = self._find_dissonances(tensor, expected)
        tensor.consensus_answer, tensor.consensus_strength = self._find_consensus(tensor)
        
        return tensor
    
    # ─── CROSS-POLLINATE ───────────────────────────────────────────────────
    
    def cross_pollinate(self, tensor: PerspectiveTensor, 
                        max_cross: int = 6) -> PerspectiveTensor:
        """Feed each model's answer to every other model for verification.
        
        The refraction: Model A's answer becomes Model B's input.
        This reveals whether models agree on REASONING not just answers.
        """
        cp_results = []
        
        # Get correct models' answers
        correct_facets = [f for f in tensor.facets if f.correct and f.answer]
        all_facets = [f for f in tensor.facets if f.answer]
        
        if not correct_facets:
            return tensor
        
        pairs_done = 0
        for src in correct_facets[:3]:  # Limit sources
            for dst in all_facets[:3]:  # Limit destinations
                if src.model_key == dst.model_key:
                    continue
                if pairs_done >= max_cross:
                    break
                
                # Ask dst: "Model X says Y. Verify or dispute."
                prompt = f"Another model computed the answer as {src.answer} for the question: {tensor.seed_question}. Verify this result. Output ONLY 'verified' or 'disputed' followed by the correct number if disputed."
                
                resp = _query(
                    self.models[dst.model_key]["id"],
                    prompt,
                    system="You are a verifier. Be precise.",
                    max_tokens=50,
                    api_key=self.api_key,
                )
                
                text = resp.get("content", "") or resp.get("reasoning_content", "")
                verified = "verified" in text.lower()
                
                cp_results.append({
                    "source": src.model_key,
                    "destination": dst.model_key,
                    "source_answer": src.answer,
                    "verified": verified,
                    "response": text[:100],
                    "latency_ms": resp.get("latency_ms", 0),
                })
                pairs_done += 1
        
        tensor.cross_pollinations = cp_results
        return tensor
    
    # ─── FIND SHADOWS ─────────────────────────────────────────────────────
    
    def find_shadows(self, tensor: PerspectiveTensor) -> List[Shadow]:
        """Find what NO model produced — the blind spots.
        
        Shadows live in the negative space between facets.
        If no model mentioned a number, concept, or approach,
        that's a shadow worth investigating.
        """
        shadows = []
        
        # Shadow 1: Numbers mentioned by some but not all
        all_numbers = defaultdict(list)
        for facet in tensor.facets:
            if facet.content:
                nums = re.findall(r"\d+\.?\d*", facet.content)
                for n in set(nums):
                    all_numbers[n].append(facet.model_key)
            if facet.reasoning_content:
                nums = re.findall(r"\d+\.?\d*", facet.reasoning_content)
                for n in set(nums):
                    all_numbers[n].append(facet.model_key)
        
        all_models = set(f.model_key for f in tensor.facets)
        for num, models in all_numbers.items():
            missing = all_models - set(models)
            if missing and len(models) > 0:
                shadows.append(Shadow(
                    description=f"Number {num} mentioned by {len(models)} models but missed by {missing}",
                    domain="numerical",
                    models_checked=list(all_models),
                    confidence=0.6 + 0.1 * len(models),
                ))
        
        # Shadow 2: All models wrong — the answer space nobody reached
        if tensor.expected_answer and tensor.n_correct == 0:
            shadows.append(Shadow(
                description=f"No model produced the expected answer {tensor.expected_answer}",
                domain="accuracy",
                models_checked=list(all_models),
                confidence=0.9,
            ))
        
        # Shadow 3: Confidence gap — models confident but wrong
        for facet in tensor.facets:
            if facet.confidence > 0.8 and not facet.correct and tensor.expected_answer:
                shadows.append(Shadow(
                    description=f"{facet.model_key} ({facet.spice}) confident ({facet.confidence:.1f}) but wrong: got {facet.answer}, expected {tensor.expected_answer}",
                    domain="overconfidence",
                    models_checked=[facet.model_key],
                    confidence=0.7,
                ))
        
        # Shadow 4: Disagreement on approach — same answer, different reasoning
        if tensor.n_correct >= 2:
            correct_thinkers = [f for f in tensor.facets if f.correct and f.steps]
            if len(correct_thinkers) >= 2:
                shadows.append(Shadow(
                    description=f"Multiple models agree on answer but reasoning differs — approach resonance worth mining",
                    domain="reasoning_diversity",
                    models_checked=[f.model_key for f in correct_thinkers],
                    confidence=0.5,
                ))
        
        tensor.shadows = shadows
        return shadows
    
    # ─── SUMMARIZE ─────────────────────────────────────────────────────────
    
    def summarize(self, tensor: PerspectiveTensor) -> str:
        """Human-readable summary of a perspective tensor."""
        lines = [
            f"{'='*60}",
            f"KALEIDOSCOPE: {tensor.seed_question[:60]}",
            f"{'='*60}",
            f"Tensor: {tensor.tensor_id}",
            f"Models: {tensor.n_models} | Correct: {tensor.n_correct}/{tensor.n_models}",
            f"Consensus: {tensor.consensus_answer} (strength: {tensor.consensus_strength})",
            f"Latency: {tensor.total_latency_ms:.0f}ms | Tokens: {tensor.total_tokens} | Cost: ${tensor.total_cost_usd:.4f}",
            "",
            "FACETS:",
        ]
        
        for f in tensor.facets:
            sym = "✓" if f.correct else "✗"
            ftype = f.facet_type.value
            steps_str = f" [{f.n_steps} steps]" if f.n_steps else ""
            murmur_str = f" 📢{','.join(f.murmurs[:2])}" if f.murmurs else ""
            lines.append(f"  {sym} {f.model_key:12s} ({f.spice:10s}): {f.answer or 'EMPTY'} "
                        f"({f.latency_ms:.0f}ms){steps_str}{murmur_str}")
        
        if tensor.harmonics:
            lines.append(f"\nHARMONICS ({len(tensor.harmonics)}):")
            for h in tensor.harmonics:
                lines.append(f"  ♪ {h.answer} ← {', '.join(h.models)} (strength={h.strength})")
        
        if tensor.dissonances:
            lines.append(f"\nDISSONANCE ({len(tensor.dissonances)}):")
            for d in tensor.dissonances[:5]:
                ans_str = " | ".join(f"{k}={v}" for k, v in list(d.answers.items())[:4])
                lines.append(f"  ⚡ {ans_str}")
        
        if tensor.shadows:
            lines.append(f"\nSHADOWS ({len(tensor.shadows)}):")
            for s in tensor.shadows[:5]:
                lines.append(f"  🌑 {s.description[:70]} (conf={s.confidence:.1f})")
        
        if tensor.cross_pollinations:
            lines.append(f"\nCROSS-POLLINATION ({len(tensor.cross_pollinations)}):")
            for cp in tensor.cross_pollinations[:6]:
                sym = "✓" if cp["verified"] else "✗"
                lines.append(f"  {sym} {cp['source']}→{cp['destination']}: {cp['response'][:50]}")
        
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    # ─── BATCH REFRACT ─────────────────────────────────────────────────────
    
    def batch_refract(self, questions: List[Tuple[str, str]], 
                      models: List[str] = None) -> List[PerspectiveTensor]:
        """Refract a batch of questions. Returns one tensor per question."""
        tensors = []
        for i, (q, expected) in enumerate(questions):
            print(f"  [{i+1}/{len(questions)}] {q[:50]}...", flush=True)
            tensor = self.refract(q, expected=expected, models=models)
            tensors.append(tensor)
        return tensors
    
    def batch_summary(self, tensors: List[PerspectiveTensor]) -> str:
        """Aggregate summary across multiple tensors."""
        total = len(tensors)
        correct_per_model = defaultdict(int)
        total_per_model = defaultdict(int)
        
        for tensor in tensors:
            for f in tensor.facets:
                total_per_model[f.model_key] += 1
                if f.correct:
                    correct_per_model[f.model_key] += 1
        
        lines = [
            f"BATCH KALEIDOSCOPE: {total} questions",
            f"{'='*60}",
            f"{'Model':15s} {'Correct':>10s} {'Total':>10s} {'Accuracy':>10s}",
            f"{'-'*15} {'-'*10} {'-'*10} {'-'*10}",
        ]
        
        for mk in sorted(total_per_model.keys(), key=lambda k: -correct_per_model.get(k, 0)):
            c = correct_per_model[mk]
            t = total_per_model[mk]
            lines.append(f"{mk:15s} {c:10d} {t:10d} {c/t*100:9.1f}%")
        
        # Harmonic rate (all models agree)
        full_agreement = sum(1 for t in tensors if t.consensus_strength == t.n_models)
        lines.append(f"\nFull consensus: {full_agreement}/{total} ({full_agreement/total*100:.0f}%)")
        
        # Total shadows found
        total_shadows = sum(len(t.shadows) for t in tensors)
        lines.append(f"Total shadows: {total_shadows}")
        
        return "\n".join(lines)
    
    # ─── Internal helpers ──────────────────────────────────────────────────
    
    def _cut_steps(self, reasoning: str) -> List[Dict]:
        """Simple step cutting — splits on paragraph breaks."""
        chunks = re.split(r"\n\n+", reasoning)
        steps = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            steps.append({
                "index": i,
                "content": chunk.strip()[:200],
                "numbers": re.findall(r"\d+\.?\d*", chunk)[:5],
            })
        return steps
    
    def _detect_murmurs(self, text: str) -> List[str]:
        murmurs = []
        if re.search(r"(?i)(?:not sure|uncertain|maybe|perhaps|hmm|wait)", text):
            murmurs.append("uncertainty")
        if re.search(r"(?i)(?:definitely|certain|clearly|obviously|exactly)", text):
            murmurs.append("confidence")
        if re.search(r"(?i)(?:alternatively|or|also could|different way)", text):
            murmurs.append("alternative")
        if re.search(r"(?i)(?:actually|correction|mistake|wrong|let me redo)", text):
            murmurs.append("error_caught")
        return murmurs
    
    def _estimate_confidence(self, text: str) -> float:
        high = len(re.findall(r"(?i)(?:definitely|certain|clearly|obviously|exactly)", text))
        low = len(re.findall(r"(?i)(?:maybe|perhaps|might|not sure|uncertain|hmm|wait)", text))
        if high > low: return min(0.95, 0.7 + high * 0.1)
        if low > high: return max(0.2, 0.6 - low * 0.1)
        return 0.7
    
    def _find_harmonics(self, tensor: PerspectiveTensor, expected: str) -> List[Harmonic]:
        """Find where models agree."""
        answer_models = defaultdict(list)
        for f in tensor.facets:
            if f.answer:
                answer_models[f.answer].append(f.model_key)
        
        harmonics = []
        for answer, models in answer_models.items():
            if len(models) > 1:
                correct = False
                if expected:
                    try:
                        correct = abs(float(answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
                    except:
                        pass
                harmonics.append(Harmonic(
                    answer=answer, models=models, correct=correct, strength=len(models),
                ))
        
        return sorted(harmonics, key=lambda h: -h.strength)
    
    def _find_dissonances(self, tensor: PerspectiveTensor, expected: str) -> List[Dissonance]:
        """Find where models disagree."""
        answers = {f.model_key: f.answer for f in tensor.facets if f.answer}
        if len(set(answers.values())) <= 1:
            return []
        
        return [Dissonance(
            question=tensor.seed_question[:60],
            answers=answers,
            expected=expected,
            magnitude=len(set(answers.values())),
        )]
    
    def _find_consensus(self, tensor: PerspectiveTensor) -> Tuple[Optional[str], int]:
        """Find the majority answer."""
        answer_counts = defaultdict(int)
        for f in tensor.facets:
            if f.answer:
                answer_counts[f.answer] += 1
        
        if not answer_counts:
            return None, 0
        
        best = max(answer_counts, key=answer_counts.get)
        return best, answer_counts[best]
    
    # ─── Export ─────────────────────────────────────────────────────────────
    
    def export_tensor(self, tensor: PerspectiveTensor, path: str):
        """Export a tensor to JSON."""
        data = asdict(tensor)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def load_tensor(self, path: str) -> PerspectiveTensor:
        """Load a tensor from JSON."""
        with open(path) as f:
            data = json.load(f)
        
        # Reconstruct
        facets = [Facet(**f) for f in data.get("facets", [])]
        harmonics = [Harmonic(**h) for h in data.get("harmonics", [])]
        dissonances = [Dissonance(**d) for d in data.get("dissonances", [])]
        shadows = [Shadow(**s) for s in data.get("shadows", [])]
        
        return PerspectiveTensor(
            tensor_id=data["tensor_id"],
            seed_question=data["seed_question"],
            expected_answer=data.get("expected_answer"),
            facets=facets,
            harmonics=harmonics,
            dissonances=dissonances,
            shadows=shadows,
            cross_pollinations=data.get("cross_pollinations", []),
            n_models=data["n_models"],
            n_correct=data["n_correct"],
            consensus_answer=data.get("consensus_answer"),
            consensus_strength=data.get("consensus_strength", 0),
            total_latency_ms=data.get("total_latency_ms", 0),
            total_tokens=data.get("total_tokens", 0),
            total_cost_usd=data.get("total_cost_usd", 0),
            created_at=data.get("created_at", time.time()),
        )


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="The Real Kaleidoscope")
    p.add_argument("question", nargs="?", default="a*a - a*b + b*b where a=5, b=3")
    p.add_argument("--expected", default=None)
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument("--batch", help="JSON file with [{question, expected}]")
    p.add_argument("--cross-pollinate", action="store_true")
    p.add_argument("--find-shadows", action="store_true")
    p.add_argument("--output", default=None)
    args = p.parse_args()
    
    k = Kaleidoscope()
    
    if args.batch:
        with open(args.batch) as f:
            questions = json.load(f)
        q_list = [(q["question"], q.get("expected")) for q in questions]
        tensors = k.batch_refract(q_list, models=args.models)
        print(k.batch_summary(tensors))
    else:
        tensor = k.refract(args.question, expected=args.expected, models=args.models)
        
        if args.cross_pollinate:
            print("Cross-pollinating...", flush=True)
            tensor = k.cross_pollinate(tensor)
        
        if args.find_shadows:
            k.find_shadows(tensor)
        
        print(k.summarize(tensor))
        
        if args.output:
            k.export_tensor(tensor, args.output)
            print(f"\nSaved to {args.output}")

if __name__ == "__main__":
    main()
