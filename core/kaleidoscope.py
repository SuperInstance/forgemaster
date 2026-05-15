#!/usr/bin/env python3
"""core/kaleidoscope.py — PLATO Holodeck Kaleidoscope

A metamorphosis engine: take an idea, refract it through N models at M steps,
accumulate the resulting tiles into a tensor of perspectives, then mine the
tensor for structure invisible to any single view.

The metaphor:
  - A single sonar ping = distance (1D + time)
  - Multiple pings from different angles = shape (3D)
  - The kaleidoscope does this for IDEAS:
    * Each model at each step is a "ping" from a different cognitive angle
    * The accumulated tiles form a tensor: models × steps × perspectives
    * Mining this tensor reveals the shape of the idea in high-dimensional space
    * You can ANIMATE the tensor — watch how understanding evolves
    * You can REFLECT on the movement — meta-calculation about the calculation

Architecture:
  1. SEED: A question or idea enters the kaleidoscope
  2. REFRACT: N models each produce their first response (N facets)
  3. DEEPEN: Each response is fed back for M rounds (temporal depth)
  4. CROSS-POLLINATE: Models read each other's tiles (spatial depth)
  5. TENSORIZE: All tiles assembled into a perspective tensor
  6. MINE: Extract structure from the tensor (convergence, divergence, resonance)
  7. ANIMATE: Replay the tensor as animation (how understanding moved)
  8. REFLECT: Meta-analysis of the pattern of movement

The tensor is:
  T[model][step][field] where:
    model ∈ {seed-mini, qwen-4b, mimo, ...}
    step ∈ {1, 2, ..., M}
    field ∈ {computation_trace, partial_result, confidence, pinna_encoding, ...}

This tensor is PRECALCULATED KNOWLEDGE — frozen at write time, mineable forever.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple, Any
from collections import defaultdict
from enum import Enum

# ─── Data Structures ──────────────────────────────────────────────────────────

class FacetType(Enum):
    """What angle does this facet view the idea from?"""
    DIRECT = "direct"           # Compute the answer directly
    DECOMPOSE = "decompose"     # Break into sub-problems
    VERIFY = "verify"           # Check a claimed answer
    PIVOT = "pivot"             # Approach from a different mathematical angle
    META = "meta"               # Reflect on the computation itself
    ADVERSARIAL = "adversarial" # Try to break/disprove the result

@dataclass
class KaleidoscopeTile:
    """One tile in the kaleidoscope tensor."""
    tile_id: str = ""
    chain_id: str = ""          # Which chain this belongs to (model + approach)
    model: str = ""             # Which model produced this
    step: int = 0               # Temporal depth (which round)
    facet: str = "direct"       # What angle (FacetType value)
    
    # The content
    computation_trace: str = ""  # Raw reasoning (from reasoning_content or content)
    partial_result: Optional[str] = None  # Extracted intermediate answer
    confidence: float = 0.0     # Convergence-derived confidence
    
    # Cognitive origin (THE NATIVE PRINCIPLE)
    cognitive_origin: str = "native"  # native | translated | cross_pollinated | bootstrapped
    draft: float = 0.0          # Measured capability depth for this tile
    safe_depth: float = 0.0     # Minimum safe depth for this model+task
    
    # Cross-pollination
    read_tiles: List[str] = field(default_factory=list)  # Which tiles this one read
    agrees_with: List[str] = field(default_factory=list)  # Which tiles agree with this result
    disagrees_with: List[str] = field(default_factory=list)  # Which tiles disagree
    
    # Meta
    latency_ms: float = 0.0
    tokens_used: int = 0
    timestamp: float = 0.0

@dataclass
class PerspectiveTensor:
    """The accumulated tensor of all kaleidoscope tiles.
    
    Shape: (n_models, n_steps, n_fields)
    
    This IS the frozen knowledge structure. It can be:
    - Mined for convergence/divergence patterns
    - Animated to see how understanding evolved
    - Reflected upon for meta-calculation
    - Sliced along any axis (per-model, per-step, per-facet)
    """
    question: str = ""
    expected: str = ""
    tiles: List[KaleidoscopeTile] = field(default_factory=list)
    
    # Index structures for fast slicing
    _by_model: Dict[str, List[KaleidoscopeTile]] = field(default_factory=dict)
    _by_step: Dict[int, List[KaleidoscopeTile]] = field(default_factory=dict)
    _by_facet: Dict[str, List[KaleidoscopeTile]] = field(default_factory=dict)
    
    def index(self):
        """Rebuild index structures."""
        self._by_model = defaultdict(list)
        self._by_step = defaultdict(list)
        self._by_facet = defaultdict(list)
        for t in self.tiles:
            self._by_model[t.model].append(t)
            self._by_step[t.step].append(t)
            self._by_facet[t.facet].append(t)
    
    def slice_model(self, model: str) -> List[KaleidoscopeTile]:
        return self._by_model.get(model, [])
    
    def slice_step(self, step: int) -> List[KaleidoscopeTile]:
        return self._by_step.get(step, [])
    
    def slice_facet(self, facet: str) -> List[KaleidoscopeTile]:
        return self._by_facet.get(facet, [])
    
    def convergence_at(self, step: int) -> Dict[str, int]:
        """How many models agree on each partial_result at this step?"""
        results = defaultdict(int)
        for t in self.slice_step(step):
            if t.partial_result:
                results[t.partial_result] += 1
        return dict(sorted(results.items(), key=lambda x: -x[1]))
    
    def resonance_map(self) -> Dict[str, List[str]]:
        """Which models agree with which across all steps?
        
        Resonance = persistent agreement across temporal depth.
        Like harmonics in a sound — the overtones that survive.
        """
        resonance = defaultdict(set)
        for step in sorted(set(t.step for t in self.tiles)):
            conv = self.convergence_at(step)
            for result, count in conv.items():
                models_with_result = [
                    t.model for t in self.slice_step(step) 
                    if t.partial_result == result
                ]
                for m in models_with_result:
                    resonance[m].add(result)
        return {k: sorted(v) for k, v in resonance.items()}
    
    def divergence_points(self) -> List[Dict]:
        """Where do models DISAGREE? These are the interesting boundary regions.
        
        Divergence ≠ error. Divergence = the edge of shared understanding.
        Like interference fringes — the pattern reveals wave structure.
        """
        divergences = []
        for step in sorted(set(t.step for t in self.tiles)):
            conv = self.convergence_at(step)
            if len(conv) > 1:  # Multiple different answers
                divergences.append({
                    "step": step,
                    "results": conv,
                    "entropy": -sum(
                        (c / sum(conv.values())) * (c / sum(conv.values()))
                        for c in conv.values()
                    ),
                })
        return divergences
    
    def animate_timeline(self) -> List[Dict]:
        """Animate the tensor: how does understanding move over steps?
        
        Each frame shows:
        - What models believed at this step
        - What changed from the previous step
        - The velocity of convergence (is it speeding up or slowing down?)
        """
        frames = []
        prev_convergence = {}
        
        for step in sorted(set(t.step for t in self.tiles)):
            conv = self.convergence_at(step)
            top_result = max(conv, key=conv.get) if conv else None
            top_count = conv.get(top_result, 0) if conv else 0
            total = sum(conv.values()) if conv else 0
            
            # Velocity: how much did convergence change?
            velocity = 0.0
            if prev_convergence:
                prev_top = max(prev_convergence, key=prev_convergence.get) if prev_convergence else None
                prev_count = prev_convergence.get(prev_top, 0) if prev_convergence else 0
                velocity = (top_count / total if total else 0) - (prev_count / sum(prev_convergence.values()) if prev_convergence else 0)
            
            frames.append({
                "step": step,
                "top_result": top_result,
                "agreement": f"{top_count}/{total}",
                "convergence_pct": top_count / total * 100 if total else 0,
                "velocity": velocity,
                "all_results": conv,
            })
            prev_convergence = conv
        
        return frames
    
    def reflect(self) -> Dict:
        """Meta-analysis: what does the PATTERN of computation tell us?
        
        This is the sonar image — the shape revealed by accumulated pings.
        Not just "what's the answer" but "what is the shape of this idea."
        """
        timeline = self.animate_timeline()
        
        # Convergence trajectory
        converging = all(
            f["convergence_pct"] >= (timeline[i-1]["convergence_pct"] if i > 0 else 0)
            for i, f in enumerate(timeline)
        )
        
        # Model accuracy ranking
        model_accuracy = {}
        for model, tiles in self._by_model.items():
            correct = sum(1 for t in tiles if t.partial_result == self.expected)
            total = len(tiles)
            model_accuracy[model] = correct / total if total else 0
        
        # Cross-pollination events
        cross_polls = sum(1 for t in self.tiles if len(t.read_tiles) > 0)
        
        return {
            "question": self.question,
            "expected": self.expected,
            "convergence_trajectory": "converging" if converging else "oscillating",
            "timeline": timeline,
            "model_accuracy": model_accuracy,
            "resonance": self.resonance_map(),
            "divergence_points": self.divergence_points(),
            "cross_pollination_events": cross_polls,
            "total_tiles": len(self.tiles),
            "total_tokens": sum(t.tokens_used for t in self.tiles),
            "total_latency_ms": sum(t.latency_ms for t in self.tiles),
        }


# ─── Kaleidoscope Engine ──────────────────────────────────────────────────────

class Kaleidoscope:
    """The refraction engine. Takes an idea, refracts it, builds the tensor."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.deepinfra.com/v1/openai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    
    def _query(self, model: str, messages: List[Dict], max_tokens: int = 200) -> Tuple[str, str, float, int]:
        """Query a model. Returns (content, reasoning, latency_ms, tokens)."""
        import requests as req
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
        start = time.time()
        try:
            r = req.post(self.url, headers=self.headers, json=payload, timeout=120)
            lat = (time.time() - start) * 1000
            if r.status_code != 200:
                return "", f"ERROR {r.status_code}", lat, 0
            d = r.json()
            msg = d["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            reasoning = (msg.get("reasoning_content") or "").strip()
            usage = d.get("usage", {})
            return content, reasoning, lat, usage.get("total_tokens", 0)
        except Exception as e:
            return "", f"ERROR {e}", (time.time() - start) * 1000, 0
    
    @staticmethod
    def _extract_num(text: str) -> Optional[str]:
        if not text: return None
        # Priority 1: "Final Answer" or "RESULT" patterns
        for pattern in [
            r'[Ff]inal [Aa]nswer:?\s*(-?\d+\.?\d*)',
            r'[Rr]esult:?\s*(-?\d+\.?\d*)',
        ]:
            m = re.search(pattern, text)
            if m: return m.group(1)
        # Priority 2: Last "= number" in the LAST line (the final computation)
        lines = text.strip().split('\n')
        for line in reversed(lines):
            eqs = re.findall(r'=\s*(-?\d+\.?\d*)', line)
            if eqs: return eqs[-1]
        # Priority 3: Last number in last line (avoid echo from prompt)
        for line in reversed(lines):
            line = line.strip()
            if not line: continue
            nums = re.findall(r'-?\d+\.?\d*', line)
            if nums: return nums[-1]
        return None
    
    def refract(
        self,
        prompt: str,
        expected: str,
        models: Dict[str, str],  # key → model_id
        n_steps: int = 3,
        cross_pollinate: bool = True,
        max_tokens_per: Dict[str, int] = None,
    ) -> PerspectiveTensor:
        """Run the full kaleidoscope on an idea.
        
        Phases:
          1. SEED: Each model produces its first response
          2. DEEPEN: Each model continues for n_steps rounds
          3. CROSS-POLLINATE: Models read each other's best tiles
          4. SYNTHESIZE: Final round with cross-pollinated context
        """
        if max_tokens_per is None:
            max_tokens_per = {}
        
        tensor = PerspectiveTensor(question=prompt, expected=expected)
        
        # Phase 1 + 2: Each model runs its own chain
        chains: Dict[str, List[KaleidoscopeTile]] = {}
        
        for model_key, model_id in models.items():
            chain = []
            mt = max_tokens_per.get(model_key, 200)
            
            for step in range(1, n_steps + 1):
                # Build context from this model's previous tiles
                prev_context = ""
                if chain:
                    prev_tiles = "\n".join(
                        f"Step {t.step}: {t.computation_trace[:300]}\n  Result so far: {t.partial_result or '?'}"
                        for t in chain[-2:]  # Read last 2 tiles only
                    )
                    prev_context = f"\n\nPrevious steps:\n{prev_tiles}"
                
                if step == n_steps:
                    sys = f"You are computing the final answer.{prev_context}\n\nGive the FINAL ANSWER as a number."
                else:
                    sys = f"You are computing step by step.{prev_context}\n\nThis is step {step}. Show your work."
                
                content, reasoning, lat, tokens = self._query(
                    model_id,
                    [
                        {"role": "system", "content": sys},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=mt,
                )
                
                # Extract: use content if present, else reasoning
                trace = reasoning if reasoning else content
                partial = self._extract_num(content) or self._extract_num(reasoning)
                
                tile = KaleidoscopeTile(
                    tile_id=str(uuid.uuid4())[:8],
                    chain_id=f"{model_key}-chain",
                    model=model_key,
                    step=step,
                    facet="direct",
                    computation_trace=trace[:600],
                    partial_result=partial,
                    confidence=1.0 if partial == expected else (0.5 if partial else 0.0),
                    latency_ms=lat,
                    tokens_used=tokens,
                    timestamp=time.time(),
                )
                chain.append(tile)
                tensor.tiles.append(tile)
                
                # Early convergence
                if step >= 2 and partial and chain[-2].partial_result == partial:
                    break
            
            chains[model_key] = chain
        
        # Phase 3: Cross-pollination
        if cross_pollinate and len(models) > 1:
            for model_key, model_id in models.items():
                # Read the BEST tile from each OTHER model
                other_tiles = []
                for other_key, other_chain in chains.items():
                    if other_key != model_key and other_chain:
                        best = max(other_chain, key=lambda t: t.confidence)
                        other_tiles.append(best)
                
                if not other_tiles:
                    continue
                
                cross_context = "\n".join(
                    f"Model {t.model} at step {t.step}: {t.computation_trace[:200]}\n  Their answer: {t.partial_result or '?'}"
                    for t in other_tiles
                )
                
                mt = max_tokens_per.get(model_key, 200)
                content, reasoning, lat, tokens = self._query(
                    model_id,
                    [
                        {"role": "system", "content": f"Other models computed:\n{cross_context}\n\nGiven their work, what is your FINAL ANSWER?"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=mt,
                )
                
                trace = reasoning if reasoning else content
                partial = self._extract_num(content) or self._extract_num(reasoning)
                
                tile = KaleidoscopeTile(
                    tile_id=str(uuid.uuid4())[:8],
                    chain_id=f"{model_key}-cross",
                    model=model_key,
                    step=n_steps + 1,
                    facet="cross_pollinated",
                    computation_trace=trace[:600],
                    partial_result=partial,
                    confidence=1.0 if partial == expected else (0.5 if partial else 0.0),
                    latency_ms=lat,
                    tokens_used=tokens,
                    timestamp=time.time(),
                    read_tiles=[t.tile_id for t in other_tiles],
                )
                tensor.tiles.append(tile)
        
        # Build agreement/disagreement
        for i, t1 in enumerate(tensor.tiles):
            for t2 in tensor.tiles[i+1:]:
                if t1.partial_result and t2.partial_result:
                    if t1.partial_result == t2.partial_result:
                        t1.agrees_with.append(t2.tile_id)
                        t2.agrees_with.append(t1.tile_id)
                    else:
                        t1.disagrees_with.append(t2.tile_id)
                        t2.disagrees_with.append(t1.tile_id)
        
        tensor.index()
        return tensor


# ─── Mining Operations ────────────────────────────────────────────────────────

def mine_tensor(tensor: PerspectiveTensor) -> Dict:
    """Extract all minable structure from a perspective tensor.
    
    This is the sonar image processor — turns pings into shape.
    """
    reflection = tensor.reflect()
    
    # Upper-dimension detection:
    # If models converge from different computation traces to the same answer,
    # that answer has higher-dimensional support (it's not a fluke of one approach)
    convergent_traces = defaultdict(list)
    for t in tensor.tiles:
        if t.partial_result:
            convergent_traces[t.partial_result].append({
                "model": t.model,
                "facet": t.facet,
                "step": t.step,
                "trace_preview": t.computation_trace[:100],
            })
    
    # The "harmonic" — results that appear across multiple models
    harmonics = {
        result: traces for result, traces in convergent_traces.items()
        if len(set(t["model"] for t in traces)) > 1
    }
    
    # The "dissonance" — where models fundamentally disagree
    dissonance = [
        {"result": result, "support": traces}
        for result, traces in convergent_traces.items()
        if result != tensor.expected and len(traces) >= 2
    ]
    
    return {
        **reflection,
        "harmonics": harmonics,
        "dissonance": dissonance,
        "n_harmonics": len(harmonics),
        "n_dissonance": len(dissonance),
    }


def format_mining_report(mined: Dict) -> str:
    """Human-readable mining report."""
    lines = []
    lines.append(f"KALEIDOSCOPE MINING REPORT")
    lines.append(f"{'='*60}")
    lines.append(f"Question: {mined['question']}")
    lines.append(f"Expected: {mined['expected']}")
    lines.append(f"Total tiles: {mined['total_tiles']}")
    lines.append(f"Total tokens: {mined['total_tokens']}")
    lines.append(f"Convergence: {mined['convergence_trajectory']}")
    lines.append("")
    
    lines.append("TIMELINE (animation frames):")
    for frame in mined.get("timeline", []):
        bar = "█" * int(frame["convergence_pct"] / 5)
        lines.append(f"  Step {frame['step']}: {frame['top_result']:>8s} ({frame['agreement']:>5s}) {bar}")
        if frame["velocity"] != 0:
            direction = "↑" if frame["velocity"] > 0 else "↓"
            lines.append(f"          velocity: {direction} {abs(frame['velocity'])*100:.0f}%")
    lines.append("")
    
    lines.append(f"HARMONICS (multi-model convergence): {mined['n_harmonics']}")
    for result, traces in mined.get("harmonics", {}).items():
        models = set(t["model"] for t in traces)
        lines.append(f"  {result}: {len(traces)} traces from {len(models)} models")
    lines.append("")
    
    lines.append(f"DISSONANCE (persistent disagreement): {mined['n_dissonance']}")
    for d in mined.get("dissonance", []):
        lines.append(f"  {d['result']}: {len(d['support'])} traces (NOT expected)")
    lines.append("")
    
    lines.append("RESONANCE MAP (what each model settled on):")
    for model, results in mined.get("resonance", {}).items():
        lines.append(f"  {model}: {results}")
    lines.append("")
    
    lines.append("MODEL ACCURACY:")
    for model, acc in sorted(mined.get("model_accuracy", {}).items(), key=lambda x: -x[1]):
        bar = "█" * int(acc * 20)
        lines.append(f"  {model:12s}: {acc*100:5.1f}% {bar}")
    
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="PLATO Kaleidoscope")
    parser.add_argument("--api-key-file", default=os.path.expanduser(
        "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt"))
    parser.add_argument("--output", default="experiments/kaleidoscope-results.json")
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--no-cross", action="store_true")
    args = parser.parse_args()
    
    with open(args.api_key_file) as f:
        api_key = f.read().strip()
    
    ks = Kaleidoscope(api_key)
    
    models = {
        "seed-mini": "ByteDance/Seed-2.0-mini",
        "qwen-4b": "Qwen/Qwen3.5-4B",
        "mimo": "XiaomiMiMo/MiMo-V2.5",
    }
    
    # Model-specific token budgets (from experiments)
    max_tokens = {
        "seed-mini": 100,
        "qwen-4b": 400,
        "mimo": 100,
    }
    
    # The questions to refract
    questions = [
        ("a*a - a*b + b*b where a=5, b=3", "19"),
        ("(a+b)*(a-b) where a=5, b=3", "16"),
        ("5*5 - 3*4 + 2*2", "17"),
    ]
    
    all_tensors = []
    
    for prompt, expected in questions:
        print(f"\n{'='*60}")
        print(f"REFRACTING: {prompt}")
        print(f"Expected: {expected}")
        print(f"{'='*60}")
        
        tensor = ks.refract(
            prompt=prompt,
            expected=expected,
            models=models,
            n_steps=args.steps,
            cross_pollinate=not args.no_cross,
            max_tokens_per=max_tokens,
        )
        
        mined = mine_tensor(tensor)
        report = format_mining_report(mined)
        print(report)
        
        all_tensors.append({
            "question": prompt,
            "expected": expected,
            "tiles": [asdict(t) for t in tensor.tiles],
            "mined": mined,
        })
    
    with open(args.output, "w") as f:
        json.dump(all_tensors, f, indent=2, default=str)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()

# ─── Navigation Layer ─────────────────────────────────────────────────────────
# The large model encodes PRINCIPLES about safe cognitive navigation.
# The small model executes PROCEDURES within those principles.
# The kaleidoscope tags each tile with its cognitive origin and safety margin.

class CognitiveOrigin(Enum):
    """Was this tile produced from native understanding or translated understanding?"""
    NATIVE = "native"           # Model's training topology directly covers this
    TRANSLATED = "translated"   # Model is mapping from a different cognitive landscape
    BOOTSTRAPPED = "bootstrapped"  # Model learned this through kaleidoscope iteration
    CROSS_POLLINATED = "cross_pollinated"  # Model read another model's native tile

@dataclass
class NavigationProfile:
    """The cognitive navigation chart for a model on a task.
    
    Like a nautical chart: shows depths, shoals, channels, and safe passages.
    """
    model: str
    task_type: str
    
    # The draft: minimum capability needed
    draft: float = 0.0  # 0.0-1.0, how deep the model needs to go
    
    # The margin: buffer for unexpected complexity
    margin: float = 0.2  # Default 20% margin
    
    # Pinnacles: known failure modes that require extra wide turns
    pinnacles: List[str] = field(default_factory=list)
    
    # Bights: well-mapped territory where shortcuts are safe
    bights: List[str] = field(default_factory=list)
    
    # Cognitive origin: native, translated, or bootstrapped
    origin: str = "native"
    
    @property
    def safe_depth(self) -> float:
        """Minimum safe cognitive depth for this model+task combination."""
        pinnacle_penalty = 0.1 * len(self.pinnacles)
        bight_credit = 0.05 * len(self.bights)
        return self.draft + self.margin + pinnacle_penalty - bight_credit
    
    def is_safe(self, measured_depth: float) -> bool:
        """Is the measured capability deep enough for this task?"""
        return measured_depth >= self.safe_depth


def compute_navigation_profile(
    model_key: str,
    task_type: str,
    accuracy_history: List[float],
    known_failure_modes: List[str] = None,
) -> NavigationProfile:
    """Compute a navigation profile from experimental history.
    
    This is the large model's job — abstract the safety principles
    that the small model can't discover on its own.
    """
    known_failure_modes = known_failure_modes or []
    
    # Draft = minimum observed accuracy (shallow side constraint)
    draft = min(accuracy_history) if accuracy_history else 0.0
    
    # Margin increases with variance (uncertain waters need more buffer)
    if len(accuracy_history) > 1:
        import statistics
        variance = statistics.variance(accuracy_history)
        margin = 0.2 + min(variance * 2, 0.3)  # 20-50% margin
    else:
        margin = 0.3  # Default high margin for unknowns
    
    # Pinnacles: categories where accuracy drops significantly
    pinnacles = []
    for failure in known_failure_modes:
        pinnacles.append(failure)
    
    # Bights: categories where accuracy is consistently high
    bights = []
    if accuracy_history and min(accuracy_history) > 0.8:
        bights.append(task_type)
    
    # Cognitive origin
    origin = "native"
    if "translated" in task_type or "cross" in task_type:
        origin = "translated"
    elif "bootstrap" in task_type:
        origin = "bootstrapped"
    
    return NavigationProfile(
        model=model_key,
        task_type=task_type,
        draft=draft,
        margin=margin,
        pinnacles=pinnacles,
        bights=bights,
        origin=origin,
    )


def augment_kaleidoscope_with_navigation(tensor: PerspectiveTensor) -> Dict:
    """Add navigation profiles to a perspective tensor.
    
    For each model, compute the cognitive navigation chart showing:
    - Where it's safe to proceed (bights)
    - Where to turn wide (pinnacles)
    - What the minimum safe depth is (draft + margin)
    - Whether its understanding is native or translated
    """
    profiles = {}
    
    for model_key in set(t.model for t in tensor.tiles):
        model_tiles = [t for t in tensor.tiles if t.model == model_key]
        
        # Accuracy across steps
        accuracies = [
            1.0 if t.partial_result == tensor.expected else 0.0
            for t in model_tiles
        ]
        
        # Failure modes (steps where model got wrong answer)
        failures = [
            f"step_{t.step}_{t.facet}"
            for t in model_tiles
            if t.partial_result != tensor.expected
        ]
        
        profile = compute_navigation_profile(
            model_key=model_key,
            task_type="arithmetic",
            accuracy_history=accuracies,
            known_failure_modes=failures,
        )
        
        profiles[model_key] = {
            "draft": profile.draft,
            "margin": profile.margin,
            "safe_depth": profile.safe_depth,
            "pinnacles": profile.pinnacles,
            "bights": profile.bights,
            "origin": profile.origin,
            "accuracy_trajectory": accuracies,
            "recommendation": _navigation_recommendation(profile, tensor.expected),
        }
    
    return profiles


def _navigation_recommendation(profile: NavigationProfile, expected: str) -> str:
    """Generate a navigation recommendation for this model on this task.
    
    Like a pilot's advice: 'turn wide around the reef, cut inside the bay.'
    """
    if profile.draft >= 0.8:
        return f"NATIVE PATHWAY: Safe to proceed at full speed. Accuracy {profile.draft:.0%}. Cut inside on bights."
    elif profile.draft >= 0.5:
        return f"TRANSLATED PATHWAY: Proceed with caution. Draft {profile.draft:.0%}, safe depth {profile.safe_depth:.0%}. Turn wide around pinnacles: {profile.pinnacles}."
    elif profile.draft > 0:
        return f"SHALLOW WATERS: Draft {profile.draft:.0%} below safe depth {profile.safe_depth:.0%}. Anchor here, send a different model. This model is running aground."
    else:
        return f"DRY GROUND: No native pathway to {expected}. This model cannot navigate here. Use only as a cross-pollination source, never as primary navigator."
