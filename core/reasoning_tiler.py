#!/usr/bin/env python3
"""core/reasoning_tiler.py — Extract frozen computation traces from thinking models.

THE KEY INSIGHT:
  reasoning_content IS the frozen PLATO tile.
  
  When a thinking model (Qwen-4B, MiMo, DeepSeek-R1) solves a problem,
  the `reasoning_content` field contains the full computation trace:
  - What it considered
  - What it tried
  - Where it got confused
  - What it rejected
  - The path it took to the answer
  
  This is MORE valuable than the answer itself because:
  1. You can REWIND to any step and branch
  2. You can MINE murmur (lightweight agent communication)
  3. You can REVERSE-ACTUALIZE from a desired answer backward
  4. You can SPREAD the trace across tools (safety valve, depth sounder)

THE TOOL:
  1. TileCutter — splits reasoning_content into step-tiles
  2. TileRewinder — branches from any step, re-runs from there
  3. MurmurExtractor — mines communication signals from traces
  4. ReverseActualizer — decomposes target into sub-tiles, assigns to models
  5. SpreadBar — fans out trace steps to hydraulic attachments

Usage:
    from core.reasoning_tiler import TileCutter, TileRewinder
    
    # Extract tiles from a thinking model's response
    tiles = TileCutter.cut(response)
    
    # Rewind to step 3 and branch
    branch = TileRewinder.rewind(tiles, step=3, new_prompt="try a different approach")
    
    # Extract murmur signals
    murmur = MurmurExtractor.mine(tiles)
    
    # Reverse-actualize from a target answer
    plan = ReverseActualizer.decompose(target="37699", model="seed-mini")
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
import statistics
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum

import requests


# ─── API Coupling ─────────────────────────────────────────────────────────────

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def _get_key():
    return open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()

def _query(model: str, prompt: str, system: str = "", max_tokens: int = 500,
           temperature: float = 0.0, api_key: str = None) -> dict:
    """Query a thinking model and capture BOTH content and reasoning_content."""
    api_key = api_key or _get_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system} if system else None,
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # Remove None messages
    payload["messages"] = [m for m in payload["messages"] if m is not None]
    
    start = time.time()
    try:
        r = requests.post(DEEPINFRA_URL, headers=headers, json=payload, timeout=120)
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
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "model": model,
            "finish_reason": d["choices"][0].get("finish_reason", ""),
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}


# ─── Data Structures ──────────────────────────────────────────────────────────

class StepType(Enum):
    """What kind of reasoning step is this?"""
    SETUP = "setup"           # Establishing context, reading the problem
    COMPUTE = "compute"       # Performing a calculation
    CHECK = "check"           # Verifying a result
    BRANCH = "branch"         # Considering alternatives
    REJECT = "reject"         # Discarding a path
    CONFIRM = "confirm"       # Confirming a result
    CONFUSE = "confuse"       # Expressing uncertainty
    CORRECT = "correct"       # Self-correction
    META = "meta"             # Metacognitive reflection
    FINALIZE = "finalize"     # Producing the final answer

class MurmurType(Enum):
    """What kind of communication signal is in this step?"""
    CONFIDENCE = "confidence"  # How sure the model is
    UNCERTAINTY = "uncertainty" # What it doesn't know
    ALTERNATIVE = "alternative" # What else it considered
    ERROR_CAUGHT = "error_caught" # Self-corrected mistake
    DECOMPOSITION = "decomposition" # Breaking problem into pieces
    DEPENDENCY = "dependency"  # What depends on what

@dataclass
class StepTile:
    """One step in a reasoning trace — a frozen PLATO tile."""
    tile_id: str
    trace_id: str
    step_index: int
    step_type: StepType
    content: str
    # What numbers appeared in this step
    numbers_mentioned: List[str] = field(default_factory=list)
    # What was computed (if compute step)
    computed_value: Optional[str] = None
    # Murmur signals
    murmurs: List[MurmurType] = field(default_factory=list)
    # Confidence (0-1, estimated from language)
    confidence: float = 0.8
    # Can we branch from here?
    branchable: bool = True
    # Timestamp
    created_at: float = field(default_factory=time.time)

@dataclass
class ReasoningTrace:
    """A complete reasoning trace from a thinking model."""
    trace_id: str
    model: str
    prompt: str
    expected_answer: Optional[str]
    # The raw reasoning_content
    raw_reasoning: str
    # The final content (answer)
    final_content: str
    # Parsed step tiles
    steps: List[StepTile] = field(default_factory=list)
    # Did the model get the right answer?
    correct: bool = False
    got_answer: Optional[str] = None
    # Metadata
    latency_ms: float = 0
    tokens_used: int = 0
    # Murmur summary
    murmur_summary: Dict[str, Any] = field(default_factory=dict)


# ─── TileCutter: Split reasoning into step-tiles ──────────────────────────────

class TileCutter:
    """Split reasoning_content into individual step-tiles.
    
    The sawmill — turns raw reasoning logs into standardized tiles.
    """
    
    # Patterns that indicate step boundaries
    STEP_BOUNDARIES = [
        r"(?i)(?:^|\n)(?:step \d+|first|second|third|next|then|now|so,|let me|let's|wait,|actually,|hmm|but|however|alternatively)",
        r"\n\n",  # Double newline = new paragraph = likely new step
        r"(?:^|\n)\d+[\.\)]\s",  # Numbered lists
    ]
    
    # Patterns that classify step types
    TYPE_PATTERNS = {
        StepType.COMPUTE: [
            r"(?i)(?:calculat|comput|equal|result|=\s*\d|gives?\s+\d|that's?\s+\d)",
            r"\d+\s*[\+\-\*\/]\s*\d+",
        ],
        StepType.CHECK: [
            r"(?i)(?:let me (?:check|verify|double)|confirm|make sure|verify)",
        ],
        StepType.BRANCH: [
            r"(?i)(?:alternatively|or maybe|could also|another way|different approach)",
        ],
        StepType.REJECT: [
            r"(?i)(?:that (?:doesn't|can't|won't)|not right|incorrect|wrong|no,|but that)",
        ],
        StepType.CONFUSE: [
            r"(?i)(?:hmm|wait|confus|not sure|uncertain|unclear|let me think)",
        ],
        StepType.CORRECT: [
            r"(?i)(?:actually|correction|I was wrong|mistake|let me redo)",
        ],
        StepType.FINALIZE: [
            r"(?i)(?:therefore|so the (?:answer|result)|in conclusion|final|the answer is)",
        ],
        StepType.META: [
            r"(?i)(?:I need to|the problem asks|let me think about|approach|strategy)",
        ],
    }
    
    # Murmur patterns
    MURMUR_PATTERNS = {
        MurmurType.CONFIDENCE: [r"(?i)(?:I'm (?:confident|sure|certain)|definitely|clearly|obviously)"],
        MurmurType.UNCERTAINTY: [r"(?i)(?:not sure|uncertain|might be|could be|maybe|perhaps|hmm|wait)"],
        MurmurType.ALTERNATIVE: [r"(?i)(?:alternatively|or|also could|another approach|different way)"],
        MurmurType.ERROR_CAUGHT: [r"(?i)(?:actually|correction|mistake|wrong|let me redo|wait, that)"],
        MurmurType.DECOMPOSITION: [r"(?i)(?:break (?:this|it) down|first...then|step by step|let's (?:first|start))"],
        MurmurType.DEPENDENCY: [r"(?i)(?:depends on|because|since|given that|based on|using the)"],
    }
    
    @classmethod
    def cut(cls, response: dict, prompt: str = "", expected: str = None) -> ReasoningTrace:
        """Cut a raw API response into a ReasoningTrace with StepTiles."""
        trace_id = str(uuid.uuid4())[:8]
        
        reasoning = response.get("reasoning_content", "")
        content = response.get("content", "")
        model = response.get("model", "unknown")
        
        # Split into steps
        steps = cls._split_into_steps(reasoning, trace_id)
        
        # Extract answer from content or reasoning
        got_answer = cls._extract_answer(content) or cls._extract_last_number(reasoning)
        correct = False
        if expected and got_answer:
            try:
                correct = abs(float(got_answer) - float(expected)) / max(abs(float(expected)), 1) < 0.05
            except:
                correct = str(got_answer).strip() == str(expected).strip()
        
        # Build murmur summary
        murmur_summary = cls._build_murmur_summary(steps)
        
        return ReasoningTrace(
            trace_id=trace_id,
            model=model,
            prompt=prompt,
            expected_answer=expected,
            raw_reasoning=reasoning,
            final_content=content,
            steps=steps,
            correct=correct,
            got_answer=got_answer,
            latency_ms=response.get("latency_ms", 0),
            tokens_used=response.get("tokens_out", 0),
            murmur_summary=murmur_summary,
        )
    
    @classmethod
    def _split_into_steps(cls, reasoning: str, trace_id: str) -> List[StepTile]:
        """Split reasoning text into step tiles."""
        if not reasoning:
            return []
        
        # Split on double newlines first, then on boundary patterns
        chunks = re.split(r"\n\n+", reasoning)
        if len(chunks) <= 1:
            # Try splitting on sentence boundaries with step indicators
            chunks = re.split(r"(?<=[.!?])\s+(?=(?:Let me|So|Now|Wait|Actually|Hmm|But|First|Next|Then))", reasoning)
        
        if not chunks or (len(chunks) == 1 and len(chunks[0]) > 500):
            # Force split every ~200 chars at sentence boundaries
            chunks = re.split(r"(?<=[.!?])\s+", reasoning)
        
        steps = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            step_type = cls._classify_step(chunk)
            numbers = re.findall(r"\d+\.?\d*", chunk)
            murmurs = cls._detect_murmurs(chunk)
            confidence = cls._estimate_confidence(chunk)
            
            # What was computed in this step?
            computed = None
            if step_type == StepType.COMPUTE:
                nums = re.findall(r"(?:=\s*|=)(-?\d+\.?\d*)", chunk)
                if nums:
                    computed = nums[-1]
            
            steps.append(StepTile(
                tile_id=f"{trace_id}_s{i}",
                trace_id=trace_id,
                step_index=i,
                step_type=step_type,
                content=chunk.strip(),
                numbers_mentioned=numbers[:5],
                computed_value=computed,
                murmurs=murmurs,
                confidence=confidence,
            ))
        
        return steps
    
    @classmethod
    def _classify_step(cls, chunk: str) -> StepType:
        """Classify a reasoning chunk by type."""
        scores = {}
        for step_type, patterns in cls.TYPE_PATTERNS.items():
            score = sum(len(re.findall(p, chunk)) for p in patterns)
            scores[step_type] = score
        
        if not scores or max(scores.values()) == 0:
            return StepType.SETUP
        
        return max(scores, key=scores.get)
    
    @classmethod
    def _detect_murmurs(cls, chunk: str) -> List[MurmurType]:
        """Detect murmur signals in a reasoning chunk."""
        murmurs = []
        for murmur_type, patterns in cls.MURMUR_PATTERNS.items():
            if any(re.search(p, chunk) for p in patterns):
                murmurs.append(murmur_type)
        return murmurs
    
    @classmethod
    def _estimate_confidence(cls, chunk: str) -> float:
        """Estimate confidence from language signals."""
        high = len(re.findall(r"(?i)(?:definitely|certain|clearly|obviously|exactly|sure|confident)", chunk))
        low = len(re.findall(r"(?i)(?:maybe|perhaps|might|could be|not sure|uncertain|hmm|wait)", chunk))
        
        if high > low:
            return min(0.95, 0.7 + high * 0.1)
        elif low > high:
            return max(0.2, 0.6 - low * 0.1)
        return 0.7
    
    @classmethod
    def _extract_answer(cls, content: str) -> Optional[str]:
        nums = re.findall(r"-?\d+\.?\d*", content)
        return nums[-1] if nums else None
    
    @classmethod
    def _extract_last_number(cls, text: str) -> Optional[str]:
        nums = re.findall(r"-?\d+\.?\d*", text)
        return nums[-1] if nums else None
    
    @classmethod
    def _build_murmur_summary(cls, steps: List[StepTile]) -> Dict:
        """Summarize murmur patterns across all steps."""
        murmur_counts = {}
        for step in steps:
            for m in step.murmurs:
                murmur_counts[m.value] = murmur_counts.get(m.value, 0) + 1
        
        confidences = [s.confidence for s in steps]
        
        # Find branch points (steps where alternatives were considered)
        branch_points = [s.step_index for s in steps if s.step_type == StepType.BRANCH
                        or MurmurType.ALTERNATIVE in s.murmurs]
        
        # Find error corrections
        error_corrections = [s.step_index for s in steps if s.step_type == StepType.CORRECT
                            or MurmurType.ERROR_CAUGHT in s.murmurs]
        
        return {
            "murmur_counts": murmur_counts,
            "avg_confidence": statistics.mean(confidences) if confidences else 0.5,
            "confidence_trajectory": [round(c, 2) for c in confidences],
            "branch_points": branch_points,
            "error_corrections": error_corrections,
            "n_steps": len(steps),
            "step_types": list(set(s.step_type.value for s in steps)),
        }


# ─── TileRewinder: Branch from any step ───────────────────────────────────────

class TileRewinder:
    """Rewind a reasoning trace to any step and branch from there.
    
    The time machine — go back to step N, inject new context, re-run.
    """
    
    @classmethod
    def rewind(cls, trace: ReasoningTrace, step: int, 
               inject: str = "", model: str = None,
               api_key: str = None) -> ReasoningTrace:
        """Rewind to step N, optionally inject new context, re-run the model.
        
        Args:
            trace: The original reasoning trace
            step: Which step to rewind to (0-indexed)
            inject: Additional context to inject at the branch point
            model: Model to use (defaults to trace's model)
            api_key: API key
            
        Returns:
            New ReasoningTrace branched from step N
        """
        if step >= len(trace.steps):
            return trace
        
        model = model or trace.model
        
        # Build the "what we know so far" context
        context_steps = trace.steps[:step + 1]
        context = "\n\n".join(s.content for s in context_steps)
        
        # Build the branch prompt
        branch_prompt = f"""You were solving this problem: {trace.prompt}

You had reasoned through these steps:

{context}

"""
        if inject:
            branch_prompt += f"""Now consider this additional information:
{inject}

"""
        branch_prompt += "Continue from here. What is the final answer?"
        
        # Re-query the model
        response = _query(model, branch_prompt, max_tokens=500, api_key=api_key)
        
        # Cut the new trace
        new_trace = TileCutter.cut(response, prompt=f"BRANCH from {trace.trace_id}@step{step}",
                                   expected=trace.expected_answer)
        
        # Tag as a branch
        new_trace.trace_id = f"{trace.trace_id}_b{step}"
        
        return new_trace
    
    @classmethod
    def rewind_to_error(cls, trace: ReasoningTrace,
                        model: str = None, api_key: str = None) -> Optional[ReasoningTrace]:
        """Rewind to the LAST error correction point and re-branch.
        
        If the model caught its own error but still got the wrong answer,
        rewind to that correction and try a different path.
        """
        corrections = trace.murmur_summary.get("error_corrections", [])
        if not corrections:
            return None
        
        last_correction = corrections[-1]
        return cls.rewind(trace, last_correction, 
                         inject="Try a completely different approach this time.",
                         model=model, api_key=api_key)
    
    @classmethod  
    def rewind_to_branch(cls, trace: ReasoningTrace, branch_index: int = 0,
                         model: str = None, api_key: str = None) -> Optional[ReasoningTrace]:
        """Rewind to a branch point and explore the alternative."""
        branches = trace.murmur_summary.get("branch_points", [])
        if branch_index >= len(branches):
            return None
        
        return cls.rewind(trace, branches[branch_index],
                         inject="Explore the alternative you considered but didn't take.",
                         model=model, api_key=api_key)
    
    @classmethod
    def get_steps_as_tiles(cls, trace: ReasoningTrace) -> List[Dict]:
        """Export all steps as PLATO-ready tile dicts."""
        return [asdict(step) for step in trace.steps]


# ─── MurmurExtractor: Mine communication signals ──────────────────────────────

class MurmurExtractor:
    """Extract lightweight communication signals from reasoning traces.
    
    The listening post — what is the model TELLING us about its state?
    """
    
    @classmethod
    def mine(cls, trace: ReasoningTrace) -> Dict:
        """Mine all murmur signals from a trace.
        
        Returns a murmur dict with:
          - confidence_curve: how confidence changed over steps
          - hesitation_points: where the model paused/uncertain
          - alternatives_seen: what other paths were considered
          - errors_caught: self-corrections
          - decomposition: how the model broke down the problem
          - key_numbers: all numbers mentioned, in order
          - cognitive_load: how many simultaneous things the model tracked
        """
        steps = trace.steps
        
        # Confidence curve
        confidence_curve = [s.confidence for s in steps]
        
        # Hesitation points (low confidence steps)
        hesitations = [
            {"step": s.step_index, "confidence": s.confidence, "content": s.content[:80]}
            for s in steps if s.confidence < 0.5
        ]
        
        # Alternatives the model saw
        alternatives = [
            {"step": s.step_index, "content": s.content[:80]}
            for s in steps if MurmurType.ALTERNATIVE in s.murmurs
        ]
        
        # Errors caught
        errors = [
            {"step": s.step_index, "content": s.content[:80]}
            for s in steps if MurmurType.ERROR_CAUGHT in s.murmurs
        ]
        
        # Decomposition pattern
        decompositions = [
            {"step": s.step_index, "content": s.content[:80]}
            for s in steps if MurmurType.DECOMPOSITION in s.murmurs
        ]
        
        # Key numbers in order
        key_numbers = []
        for s in steps:
            key_numbers.extend(s.numbers_mentioned)
        
        # Cognitive load: how many numbers per step
        loads = [len(s.numbers_mentioned) for s in steps]
        peak_load = max(loads) if loads else 0
        avg_load = statistics.mean(loads) if loads else 0
        
        # Phase transitions: where confidence drops or rises sharply
        transitions = []
        for i in range(1, len(confidence_curve)):
            delta = confidence_curve[i] - confidence_curve[i-1]
            if abs(delta) > 0.15:
                transitions.append({
                    "from_step": i-1, "to_step": i,
                    "delta": round(delta, 2),
                    "direction": "rise" if delta > 0 else "drop",
                })
        
        return {
            "trace_id": trace.trace_id,
            "model": trace.model,
            "correct": trace.correct,
            "confidence_curve": confidence_curve,
            "avg_confidence": statistics.mean(confidence_curve) if confidence_curve else 0,
            "hesitations": hesitations,
            "alternatives": alternatives,
            "errors_caught": errors,
            "decompositions": decompositions,
            "key_numbers": key_numbers,
            "cognitive_load": {"peak": peak_load, "avg": round(avg_load, 1)},
            "phase_transitions": transitions,
            "n_steps": len(steps),
        }
    
    @classmethod
    def compare_traces(cls, traces: List[ReasoningTrace]) -> Dict:
        """Compare murmur signals across multiple models on the same problem.
        
        Like the kaleidoscope — refract one problem through multiple minds.
        """
        murmurs = [cls.mine(t) for t in traces]
        
        # Where do models agree on confidence?
        if len(murmurs) >= 2 and all(len(m["confidence_curve"]) > 0 for m in murmurs):
            # Align by step index (min length)
            min_len = min(len(m["confidence_curve"]) for m in murmurs)
            agreement = []
            for i in range(min_len):
                vals = [m["confidence_curve"][i] for m in murmurs]
                spread = max(vals) - min(vals)
                agreement.append({"step": i, "spread": round(spread, 2), "avg": round(statistics.mean(vals), 2)})
        else:
            agreement = []
        
        # Common errors
        all_errors = []
        for m in murmurs:
            all_errors.extend(m["errors_caught"])
        
        return {
            "n_traces": len(traces),
            "models": [t.model for t in traces],
            "correct_mask": [t.correct for t in traces],
            "confidence_agreement": agreement,
            "common_errors": all_errors,
            "murmurs": murmurs,
        }


# ─── ReverseActualizer: Work backward from target ─────────────────────────────

class ReverseActualizer:
    """Decompose a target answer into sub-tasks assignable to the right models.
    
    The architect — given WHAT we want, figure out HOW to get there,
    working backward from the answer to the input.
    """
    
    # Which models are best for which step types
    STEP_MODEL_ROUTING = {
        StepType.COMPUTE: "seed-mini",      # Arithmetic → Seed-mini
        StepType.CHECK: "hermes-70b",        # Quick verify → Hermes (fastest)
        StepType.BRANCH: "seed-mini",        # Explore alternatives → Seed-mini
        StepType.FINALIZE: "seed-mini",      # Final answer → Seed-mini
        StepType.SETUP: "qwen2.5-72b",       # Context setup → Qwen (thorough)
        StepType.CONFUSE: "seed-mini",       # Uncertainty → Seed-mini (reliable)
    }
    
    @classmethod
    def decompose(cls, target: str, context: str = "",
                  model: str = "Qwen/Qwen3.5-4B",
                  api_key: str = None) -> Dict:
        """Decompose a target answer into sub-tasks.
        
        Ask a thinking model: "What steps would lead to this answer?"
        Then parse the reasoning_content to extract the sub-tasks.
        
        Args:
            target: The desired answer (e.g., "37699")
            context: The problem context (e.g., "hydraulic force calculation")
            model: Thinking model to use for decomposition
            api_key: API key
            
        Returns:
            Dict with sub_tasks, each assigned to the best model
        """
        prompt = f"""Work BACKWARD from this answer: {target}
{"Context: " + context if context else ""}

Show me every computation step that would produce this answer.
For each step, explain what was computed and why."""
        
        response = _query(model, prompt, max_tokens=1000, api_key=api_key)
        trace = TileCutter.cut(response, prompt=f"REVERSE:{target}", expected=target)
        
        # Assign each step to the best model
        sub_tasks = []
        for step in trace.steps:
            best_model = cls.STEP_MODEL_ROUTING.get(step.step_type, "seed-mini")
            sub_tasks.append({
                "task_id": step.tile_id,
                "step_type": step.step_type.value,
                "description": step.content[:120],
                "assigned_model": best_model,
                "numbers": step.numbers_mentioned,
                "confidence": step.confidence,
                "computed": step.computed_value,
            })
        
        return {
            "target": target,
            "context": context,
            "decomposition_model": model,
            "n_sub_tasks": len(sub_tasks),
            "sub_tasks": sub_tasks,
            "trace_id": trace.trace_id,
            "confidence_curve": [s.confidence for s in trace.steps],
        }
    
    @classmethod
    def execute_reverse(cls, decomposition: Dict, api_key: str = None) -> Dict:
        """Execute a reverse-actualization plan step by step.
        
        Runs each sub-task through its assigned model and verifies
        the accumulated result reaches the target.
        """
        results = []
        accumulated = None
        
        for task in decomposition["sub_tasks"]:
            model_key = task["assigned_model"]
            
            # Map short names to full model IDs
            model_map = {
                "seed-mini": "ByteDance/Seed-2.0-mini",
                "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
                "qwen2.5-72b": "Qwen/Qwen2.5-72B-Instruct",
                "gemini-lite": "google/gemini-3.1-flash-lite",
            }
            model_id = model_map.get(model_key, "ByteDance/Seed-2.0-mini")
            
            # Build context from previous steps
            prev_context = ""
            if results:
                prev_context = "Previous steps found: " + ", ".join(
                    f"{r['computed']}" for r in results if r.get("computed")
                )
            
            prompt = task["description"]
            if prev_context:
                prompt = f"{prev_context}\n\nNow: {prompt}"
            
            resp = _query(model_id, f"Compute. Output ONLY the number. {prompt}", 
                         max_tokens=100, api_key=api_key)
            
            content = resp.get("content", "")
            reasoning = resp.get("reasoning_content", "")
            text = content if content else reasoning
            
            nums = re.findall(r"-?\d+\.?\d*", text)
            got = nums[-1] if nums else None
            
            results.append({
                "task_id": task["task_id"],
                "model": model_key,
                "got": got,
                "computed": got,
                "latency_ms": resp.get("latency_ms", 0),
            })
        
        # Check if final result matches target
        final = results[-1]["got"] if results else None
        target = decomposition["target"]
        correct = False
        if final and target:
            try:
                correct = abs(float(final) - float(target)) / max(abs(float(target)), 1) < 0.05
            except:
                pass
        
        return {
            "target": target,
            "final_result": final,
            "correct": correct,
            "steps_executed": len(results),
            "results": results,
        }


# ─── SpreadBar: Fan out trace steps to hydraulic tools ────────────────────────

class SpreadBar:
    """Fan out reasoning trace steps to the hydraulic attachment catalog.
    
    The distribution bar — each step goes to the right tool.
    """
    
    @classmethod
    def spread(cls, trace: ReasoningTrace, api_key: str = None) -> Dict:
        """Spread a reasoning trace across hydraulic tools.
        
        Each step type routes to the right attachment:
          COMPUTE → snap_tool (verify the computation)
          CHECK   → safety_valve (is the result safe?)
          BRANCH  → kaleidoscope_ping (refract through multiple models)
          CONFUSE → depth_sounder (check if model can handle this)
          REJECT  → residue_reader (why was this path rejected?)
        """
        from core.seed_tools import snap_tool, safety_valve, residue_reader, depth_sounder
        
        results = {
            "trace_id": trace.trace_id,
            "correct": trace.correct,
            "tool_outputs": [],
        }
        
        for step in trace.steps:
            output = {"step": step.step_index, "type": step.step_type.value}
            
            if step.step_type == StepType.COMPUTE and step.computed_value:
                # Verify computation with snap_tool
                try:
                    a = float(step.numbers_mentioned[0]) if len(step.numbers_mentioned) > 0 else 0
                    b = float(step.numbers_mentioned[1]) if len(step.numbers_mentioned) > 1 else 0
                    snap = snap_tool(a, b, api_key=api_key)
                    output["tool"] = "snap"
                    output["verified"] = snap["correct"]
                    output["result"] = snap["result"]
                except:
                    output["tool"] = "snap"
                    output["verified"] = None
            
            elif step.step_type == StepType.CHECK:
                output["tool"] = "safety_valve"
                output["confidence"] = step.confidence
                output["safe"] = step.confidence > 0.7
            
            elif step.step_type == StepType.REJECT:
                if trace.expected_answer and step.computed_value:
                    residue = residue_reader(trace.expected_answer, step.computed_value, step.content)
                    output["tool"] = "residue_reader"
                    output["residue_class"] = residue["class"]
                    output["diagnosis"] = residue["diagnosis"]
                else:
                    output["tool"] = "residue_reader"
                    output["note"] = "no computed value to diagnose"
            
            elif step.step_type == StepType.CONFUSE:
                output["tool"] = "depth_sounder"
                output["confidence"] = step.confidence
                output["depth_assessment"] = "shallow" if step.confidence < 0.5 else "navigable"
            
            else:
                output["tool"] = "none"
            
            results["tool_outputs"].append(output)
        
        return results
    
    @classmethod
    def spread_summary(cls, spread_result: Dict) -> str:
        """Human-readable summary of a spread analysis."""
        lines = [f"Spread Analysis: trace={spread_result['trace_id']} correct={spread_result['correct']}"]
        
        for out in spread_result["tool_outputs"]:
            tool = out.get("tool", "?")
            step = out["step"]
            stype = out["type"]
            
            if tool == "snap":
                lines.append(f"  Step {step} ({stype}): snap → verified={out.get('verified')}")
            elif tool == "safety_valve":
                lines.append(f"  Step {step} ({stype}): safety → safe={out.get('safe')} conf={out.get('confidence', 0):.1f}")
            elif tool == "residue_reader":
                lines.append(f"  Step {step} ({stype}): residue → {out.get('residue_class', '?')}: {out.get('diagnosis', '?')}")
            elif tool == "depth_sounder":
                lines.append(f"  Step {step} ({stype}): depth → {out.get('depth_assessment', '?')}")
            else:
                lines.append(f"  Step {step} ({stype}): {tool}")
        
        return "\n".join(lines)


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reasoning Tiler — extract frozen computation traces")
    sub = parser.add_subparsers(dest="cmd")
    
    # trace: run a thinking model and cut tiles
    trace_p = sub.add_parser("trace", help="Run a thinking model and cut tiles")
    trace_p.add_argument("prompt", help="The prompt to send")
    trace_p.add_argument("--model", default="Qwen/Qwen3.5-4B", help="Thinking model")
    trace_p.add_argument("--expected", default=None, help="Expected answer")
    trace_p.add_argument("--max-tokens", type=int, default=500)
    
    # rewind: branch from a step
    rewind_p = sub.add_parser("rewind", help="Rewind a trace from a JSON file")
    rewind_p.add_argument("trace_file", help="JSON file with saved trace")
    rewind_p.add_argument("--step", type=int, default=0, help="Step to rewind to")
    rewind_p.add_argument("--inject", default="", help="Additional context")
    
    # murmur: mine communication signals
    murmur_p = sub.add_parser("murmur", help="Mine murmur signals from a trace file")
    murmur_p.add_argument("trace_file", help="JSON file with saved trace")
    
    # reverse: reverse-actualize from a target
    reverse_p = sub.add_parser("reverse", help="Reverse-actualize from a target answer")
    reverse_p.add_argument("target", help="Target answer")
    reverse_p.add_argument("--context", default="", help="Problem context")
    
    args = parser.parse_args()
    
    if args.cmd == "trace":
        print(f"Querying {args.model}...", flush=True)
        resp = _query(args.model, args.prompt, max_tokens=args.max_tokens)
        trace = TileCutter.cut(resp, prompt=args.prompt, expected=args.expected)
        
        print(f"\nTrace: {trace.trace_id} ({len(trace.steps)} steps)")
        print(f"Answer: {trace.got_answer} (expected: {trace.expected_answer}) {'✓' if trace.correct else '✗'}")
        print(f"Content: {trace.final_content[:100]}")
        print(f"\nSteps:")
        for s in trace.steps:
            murmur_str = ",".join(m.value for m in s.murmurs) if s.murmurs else ""
            print(f"  {s.step_index:2d} [{s.step_type.value:8s}] conf={s.confidence:.1f} nums={s.numbers_mentioned[:3]} {'📢'+murmur_str if murmur_str else ''}")
            print(f"     {s.content[:90]}...")
        
        # Save
        out_file = f"experiments/trace_{trace.trace_id}.json"
        with open(out_file, "w") as f:
            json.dump(asdict(trace), f, indent=2, default=str)
        print(f"\nSaved to {out_file}")
    
    elif args.cmd == "rewind":
        with open(args.trace_file) as f:
            data = json.load(f)
        trace = ReasoningTrace(**{k: v for k, v in data.items() if k != "steps"})
        trace.steps = [StepTile(**s) for s in data.get("steps", [])]
        
        print(f"Rewinding {trace.trace_id} to step {args.step}...")
        branch = TileRewinder.rewind(trace, args.step, inject=args.inject)
        
        print(f"Branch: {branch.trace_id} ({len(branch.steps)} steps)")
        print(f"Answer: {branch.got_answer} (expected: {trace.expected_answer}) {'✓' if branch.correct else '✗'}")
    
    elif args.cmd == "murmur":
        with open(args.trace_file) as f:
            data = json.load(f)
        trace = ReasoningTrace(**{k: v for k, v in data.items() if k != "steps"})
        trace.steps = [StepTile(**s) for s in data.get("steps", [])]
        
        murmur = MurmurExtractor.mine(trace)
        print(f"Murmur Analysis: {murmur['trace_id']}")
        print(f"  Avg confidence: {murmur['avg_confidence']:.2f}")
        print(f"  Hesitations: {len(murmur['hesitations'])}")
        print(f"  Alternatives: {len(murmur['alternatives'])}")
        print(f"  Errors caught: {len(murmur['errors_caught'])}")
        print(f"  Cognitive load: peak={murmur['cognitive_load']['peak']}, avg={murmur['cognitive_load']['avg']}")
        print(f"  Phase transitions: {len(murmur['phase_transitions'])}")
        for t in murmur["phase_transitions"]:
            print(f"    Step {t['from_step']}→{t['to_step']}: {t['direction']} Δ{t['delta']}")
    
    elif args.cmd == "reverse":
        print(f"Reverse-actualizing: target={args.target} context={args.context or 'none'}")
        decomp = ReverseActualizer.decompose(args.target, context=args.context)
        
        print(f"\nDecomposition: {decomp['n_sub_tasks']} sub-tasks")
        for task in decomp["sub_tasks"]:
            print(f"  {task['task_id']} [{task['step_type']:8s}] → {task['assigned_model']:12s} conf={task['confidence']:.1f}")
            print(f"     {task['description'][:80]}")


if __name__ == "__main__":
    main()
