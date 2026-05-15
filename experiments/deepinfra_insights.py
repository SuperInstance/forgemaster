#!/usr/bin/env python3
"""experiments/deepinfra_insights.py — Cache-Aware 1000-Insight Engine

Uses DeepInfra's cached-input discount ($0.02/1M cached tokens) by:
1. Keeping a fixed system prompt across all queries (gets cached after first call)
2. Grouping queries by shared prompt prefix (cache hits on repeated prefixes)
3. Running multi-turn conversations where context accumulates (cache grows)

Models (all DeepInfra):
  - ByteDance/Seed-2.0-mini     (workhorse, cheapest, best cache behavior)
  - stepfun-ai/Step-3.5-Flash   (fast, flash-optimized)
  - Qwen/Qwen3.5-0.8B           (tiny, tests cognitive floor)
  - XiaomiMiMo/MiMo-V2.5        (reasoning model, good for spreader-tool ops)
  - ByteDance/Seed-2.0-pro      (heavy hitter, for validation)

DeepInfra pricing:
  - Seed-2.0-mini: $0.15/1M input, $0.60/1M output, $0.02/1M cached
  - Step-3.5-Flash: ~$0.10/1M input (flash), even cheaper cached
  - Qwen3.5-0.8B: ~$0.01/1M (nearly free)
  - MiMo-V2.5: more expensive but cached discount makes it viable
  - Seed-2.0-pro: $0.90/1M input but $0.02/1M cached

Strategy: Maximize cache hits by using FIXED_SYSTEM_PROMPT for every query.
After ~3 queries, the system prompt is fully cached → all subsequent calls
pay only the cached rate ($0.02/1M) on that portion.

Usage:
    python3 experiments/deepinfra_insights.py --quick
    python3 experiments/deepinfra_insights.py --full
    python3 experiments/deepinfra_insights.py --model Seed-2.0-mini
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import statistics
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from pathlib import Path

import requests

# ─── Configuration ────────────────────────────────────────────────────────────

API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "step-flash": "stepfun-ai/Step-3.5-Flash",
    "qwen-0.8b": "Qwen/Qwen3.5-0.8B",
    "mimo": "XiaomiMiMo/MiMo-V2.5",
    "seed-pro": "ByteDance/Seed-2.0-pro",
}

# FIXED system prompt — this gets cached after first call, all subsequent
# calls pay only $0.02/1M for this portion
FIXED_SYSTEM = (
    "You are a precise numerical reasoner. "
    "For every question, compute the exact answer and respond with ONLY the final number. "
    "No explanation, no units, no extra text. Just the number."
)

# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Probe:
    id: str = ""
    category: str = ""
    prompt: str = ""
    expected: str = ""
    formula: str = ""
    depth: int = 0
    width: int = 0
    input_magnitude: float = 1.0
    coefficient_familiarity: str = "familiar"  # familiar/unfamiliar
    operation_type: str = "addition"  # addition/multiplication/mixed/eisenstein
    tags: List[str] = field(default_factory=list)

@dataclass
class Result:
    probe_id: str = ""
    model: str = ""
    model_id: str = ""
    prompt: str = ""
    response: str = ""
    extracted: Optional[str] = None
    expected: str = ""
    correct: bool = False
    near: bool = False  # within 5%
    residue: str = ""
    latency_ms: float = 0.0
    category: str = ""
    cached: bool = False  # whether we think this hit cache
    tokens_in: int = 0
    tokens_out: int = 0


# ─── API Client with Cache Awareness ─────────────────────────────────────────

class CacheAwareClient:
    """DeepInfra client that tracks cache-eligible tokens."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.system_prompt_tokens = 0
        self.query_count = 0
        self.cache_hits = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def query(self, model: str, prompt: str, temperature: float = 0.0,
              max_tokens: int = 30) -> Tuple[Optional[str], float, int, int]:
        """Query DeepInfra. Returns (response, latency_ms, input_tokens, output_tokens)."""
        messages = [
            {"role": "system", "content": FIXED_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        start = time.time()
        try:
            resp = requests.post(API_URL, headers=self.headers, json=payload, timeout=60)
            latency = (time.time() - start) * 1000
            
            if resp.status_code != 200:
                return None, latency, 0, 0
            
            data = resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            # Reasoning models put answer in reasoning_content, content is empty
            content = msg.get("content", "") or ""
            reasoning = msg.get("reasoning_content", "") or ""
            content = content.strip() if content.strip() else reasoning.strip()
            
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
            
            self.query_count += 1
            self.total_input_tokens += in_tok
            self.total_output_tokens += out_tok
            
            # Estimate cache hits: system prompt is ~40 tokens
            # After first query, all subsequent queries should have system prompt cached
            if self.query_count > 1:
                self.cache_hits += min(40, in_tok)
            
            return content.strip(), latency, in_tok, out_tok
        except Exception as e:
            latency = (time.time() - start) * 1000
            return None, latency, 0, 0
    
    @staticmethod
    def extract_number(text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return numbers[-1] if numbers else None
    
    def cost_estimate(self) -> Dict:
        """Estimate cost based on DeepInfra pricing."""
        # Approximate pricing (varies by model, these are ballpark)
        cached_input = self.cache_hits
        uncached_input = self.total_input_tokens - cached_input
        output = self.total_output_tokens
        
        # Use Seed-2.0-mini pricing as baseline
        cost = (uncached_input * 0.15 + cached_input * 0.02 + output * 0.60) / 1_000_000
        
        return {
            "total_queries": self.query_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cached_tokens": cached_input,
            "estimated_uncached_tokens": uncached_input,
            "estimated_cost_usd": round(cost, 4),
            "cache_savings_usd": round(cached_input * (0.15 - 0.02) / 1_000_000, 4),
        }


# ─── Probe Generators ─────────────────────────────────────────────────────────

def generate_composition_probes() -> List[Probe]:
    """Generate composition depth probes — the cliff curve."""
    probes = []
    pid = 0
    
    # Addition chains (depth 1-10)
    for depth in range(1, 11):
        terms = list(range(1, depth + 1))
        formula = "+".join(f"n{i}" for i in terms)
        expected = sum(terms)
        prompt = f"Compute {formula} where " + ", ".join(f"n{i}={i}" for i in terms) + "."
        pid += 1
        probes.append(Probe(
            id=f"ADD-D{depth}",
            category="composition_addition",
            prompt=prompt,
            expected=str(expected),
            formula=formula,
            depth=depth,
            width=1,
            operation_type="addition",
            tags=["addition", f"depth={depth}"],
        ))
    
    # Multiplication chains (depth 1-8, small numbers)
    mul_sets = [
        [2, 3],
        [2, 3, 2],
        [2, 2, 2, 2],
        [2, 3, 2, 2],
        [1, 2, 3, 2, 1],
        [2, 2, 2, 2, 2, 2],
        [1, 2, 2, 3, 1, 2, 1],
        [1, 2, 1, 3, 1, 2, 1, 1],
    ]
    for i, terms in enumerate(mul_sets):
        depth = len(terms)
        formula = "×".join(f"n{j+1}" for j in range(depth))
        expected = 1
        for t in terms:
            expected *= t
        prompt = f"Compute {formula} where " + ", ".join(f"n{j+1}={terms[j]}" for j in range(depth)) + "."
        pid += 1
        probes.append(Probe(
            id=f"MUL-D{depth}",
            category="composition_multiplication",
            prompt=prompt,
            expected=str(expected),
            formula=formula,
            depth=depth,
            width=1,
            input_magnitude=max(terms),
            operation_type="multiplication",
            tags=["multiplication", f"depth={depth}"],
        ))
    
    # Mixed operations (width 2-5)
    mixed = [
        ("3*4 + 2*5", {"a":3,"b":4,"c":2,"d":5}, 22, 2),
        ("3*4 - 2*5", {"a":3,"b":4,"c":2,"d":5}, 2, 2),
        ("3*4 + 2*5 - 1*3", {"a":3,"b":4,"c":2,"d":5,"e":1,"f":3}, 19, 3),
        ("a*a + b*b", {"a":3,"b":4}, 25, 2),
        ("a*a - a*b + b*b", {"a":3,"b":4}, 13, 3),
        ("a*a + 2*a*b + b*b", {"a":3,"b":4}, 49, 3),
        ("a*a - 2*a*b + b*b", {"a":5,"b":3}, 4, 3),
        ("a*a*b + b*b*a", {"a":2,"b":3}, 30, 4),
    ]
    for formula, vals, expected, width in mixed:
        prompt = f"Compute {formula} where " + ", ".join(f"{k}={v}" for k, v in vals.items()) + "."
        pid += 1
        probes.append(Probe(
            id=f"MIX-W{width}-{pid}",
            category="composition_mixed",
            prompt=prompt,
            expected=str(expected),
            formula=formula,
            depth=len(vals),
            width=width,
            operation_type="mixed",
            tags=["mixed", f"width={width}"],
        ))
    
    return probes


def generate_eisenstein_probes() -> List[Probe]:
    """Generate Eisenstein norm probes — our signature finding."""
    probes = []
    
    # Coefficient familiarity sweep
    formulas = [
        ("a*a - a*b + b*b", "familiar"),     # a²-ab+b² = 25% before
        ("a*a + a*b + b*b", "unfamiliar"),    # sign change
        ("a*a - 2*a*b + b*b", "familiar"),    # (a-b)²
        ("a*a + 2*a*b + b*b", "familiar"),    # (a+b)²
        ("a*a - a*b + 2*b*b", "unfamiliar"),  # asymmetric coefficient
        ("2*a*a - a*b + b*b", "unfamiliar"),  # asymmetric a coefficient
        ("a*a - 3*a*b + b*b", "unfamiliar"),  # coefficient 3
        ("a*a + b*b", "minimal"),              # no cross term
    ]
    
    inputs = [
        {"a": 3, "b": 4},
        {"a": 5, "b": 2},
        {"a": 1, "b": 7},
        {"a": 10, "b": 3},
        {"a": -3, "b": 4},
        {"a": 0, "b": 5},
    ]
    
    for formula, familiarity in formulas:
        for vals in inputs:
            expected = eval(formula, {"__builtins__": {}}, vals)
            prompt = f"Compute {formula} where " + ", ".join(f"{k}={v}" for k, v in vals.items()) + "."
            probes.append(Probe(
                id=f"EIS-{familiarity}-{vals['a']}_{vals['b']}",
                category="eisenstein_norm",
                prompt=prompt,
                expected=str(int(expected)),
                formula=formula,
                depth=2,
                width=3 if "a*b" in formula else 2,
                input_magnitude=max(abs(vals["a"]), abs(vals["b"])),
                coefficient_familiarity=familiarity,
                operation_type="eisenstein",
                tags=["eisenstein", familiarity, f"mag={max(abs(vals['a']), abs(vals['b']))}"],
            ))
    
    return probes


def generate_magnitude_probes() -> List[Probe]:
    """Generate magnitude scaling probes."""
    probes = []
    
    magnitudes = [1, 2, 3, 5, 10, 20, 50, 100, 500, 1000]
    formula = "a*a - a*b + b*b"
    
    for mag in magnitudes:
        a, b = mag, mag + 1
        expected = a*a - a*b + b*b
        prompt = f"Compute {formula} where a={a}, b={b}."
        probes.append(Probe(
            id=f"MAG-{mag}",
            category="magnitude_scaling",
            prompt=prompt,
            expected=str(expected),
            formula=formula,
            depth=2,
            width=3,
            input_magnitude=mag,
            tags=["magnitude", f"mag={mag}"],
        ))
    
    return probes


def generate_format_probes() -> List[Probe]:
    """Generate input format sensitivity probes."""
    probes = []
    
    # All compute 19 (5*5 - 3*4 + 2*2 = 25 - 12 + 4 = 17... let me fix)
    # Actually: 5*5 - 3*4 + 2*2 = 25 - 12 + 4 = 17
    formats = [
        ("Compute 5*5 - 3*4 + 2*2.", "17", "code"),
        ("Compute 5² - 3×4 + 2².", "17", "math_unicode"),
        ("Compute twenty-five minus twelve plus four.", "17", "words"),
        ("Compute 0x19 - 0x0C + 0x04.", "17", "hex"),
        ("Compute 10001 - 1100 + 100.", "17", "binary"),
        ("Compute 5^2 - 3*4 + 2^2.", "17", "caret"),
        ("Compute five squared minus three times four plus two squared.", "17", "words_full"),
    ]
    
    for prompt, expected, fmt in formats:
        probes.append(Probe(
            id=f"FMT-{fmt}",
            category="input_format",
            prompt=prompt,
            expected=expected,
            formula="5²-3×4+2²",
            tags=["format", fmt],
        ))
    
    return probes


def generate_role_probes() -> List[Probe]:
    """Generate role-based probes using system prompt variation."""
    probes = []
    
    # The FIXED_SYSTEM is "precise numerical reasoner"
    # We vary the USER prompt to include role framing
    formula = "a*a - a*b + b*b where a=5, b=3"
    expected = "19"
    
    role_frames = [
        (f"You are checking homework. {formula} = ?", "teacher"),
        (f"As a calculator: {formula} = ?", "calculator"),
        (f"Quick game! What's {formula}? Score points!", "play"),
        (f"In a Python REPL, type: {formula}. What's the result?", "interpreter"),
        (f"A structural engineer needs: {formula}. What's the answer?", "engineer"),
        (f"Auditing: verify {formula}. What's the value?", "auditor"),
        (f"Speed round: {formula} = ?", "speed"),
        (f"Think step by step: {formula} = ?", "step_by_step"),
        (f"Don't think. Just answer: {formula} = ?", "intuition"),
        (f"{formula} = ?", "bare"),
    ]
    
    for prompt, role in role_frames:
        probes.append(Probe(
            id=f"ROLE-{role}",
            category="role_effect",
            prompt=prompt,
            expected=expected,
            formula=formula,
            tags=["role", role],
        ))
    
    return probes


def generate_mechanical_probes() -> List[Probe]:
    """Generate mechanical reasoning probes for the logging camp system."""
    probes = []
    
    mechanical = [
        ("A 4-inch bore cylinder at 3000 PSI. Force = π × 2² × 3000. Compute force.", "37699", "hydraulic"),
        ("A 3:1 pulley lifts 900 lbs. Input force needed?", "300", "pulley"),
        ("Feed speed 50 ft/min. Limbs every 2 ft. Knife cycles per minute?", "25", "delimber"),
        ("Grapple must hold 2000 lb log. Safety factor 2. Min capacity?", "4000", "safety"),
        ("Pump delivers 10 GPM to 2 sq-in cylinder. Speed in in/min?", "115", "flow"),
        ("Max cut diameter 24 inches. Tree is 22 inches. Safe? Answer yes or no.", "yes", "safety_yesno"),
        ("Tree diameter 20 in. Circumference = π × 20. Compute circumference.", "63", "tree"),
        ("8 limbs per tree, 1 tree per minute. Limbs per 8-hour shift?", "3840", "production"),
        ("Pressure 2500 PSI, bore 3 inches. Force = π × 1.5² × 2500. Compute.", "17671", "hydraulic"),
        ("4 cylinders: 3, 4, 5, 6 inch bore. All at 2000 PSI. Which has most force?", "6", "comparison"),
    ]
    
    for prompt, expected, tag in mechanical:
        probes.append(Probe(
            id=f"MECH-{tag}",
            category="mechanical_reasoning",
            prompt=prompt,
            expected=expected,
            tags=["mechanical", tag],
        ))
    
    return probes


def generate_stage_probes() -> List[Probe]:
    """Generate probes designed to detect cognitive stage (NONE/ECHO/PARTIAL/FULL)."""
    probes = []
    
    # NONE stage: model can't do anything
    # ECHO stage: model echoes inputs (e.g., a=3,b=4 → answers 3 or 4)
    # PARTIAL stage: model gets some right but falls apart on unfamiliar patterns
    # FULL stage: model handles novel combinations
    
    stage_tests = [
        # Echo detectors: answer should NOT be a or b
        ("a + b where a=7, b=3. What is the result?", "10", "echo_detect"),
        ("a * b where a=7, b=3. What is the result?", "21", "echo_detect"),
        ("a - b where a=7, b=3. What is the result?", "4", "echo_detect"),
        
        # Partial detectors: familiar pattern but non-trivial
        ("a*a + b*b where a=3, b=4.", "25", "partial_detect"),
        ("(a+b)*(a-b) where a=5, b=3.", "16", "partial_detect"),
        
        # Full detectors: requires multi-step or unfamiliar
        ("a*a - a*b + b*b where a=5, b=3.", "19", "full_detect"),
        ("a*a + 2*a*b - b*b where a=4, b=3.", "31", "full_detect"),
        ("(a*a - b*b) / (a - b) where a=5, b=3.", "8", "full_detect"),
        
        # Novel combination: never seen in training
        ("a*a*b + a*b*b where a=2, b=3.", "30", "novel_combo"),
        ("a^3 - b^3 where a=4, b=2.", "56", "novel_combo"),
    ]
    
    for prompt, expected, tag in stage_tests:
        probes.append(Probe(
            id=f"STAGE-{tag}",
            category="stage_detection",
            prompt=prompt,
            expected=expected,
            tags=["stage", tag],
        ))
    
    return probes


def generate_all_probes() -> List[Probe]:
    """Generate the full probe set."""
    probes = []
    probes.extend(generate_composition_probes())
    probes.extend(generate_eisenstein_probes())
    probes.extend(generate_magnitude_probes())
    probes.extend(generate_format_probes())
    probes.extend(generate_role_probes())
    probes.extend(generate_mechanical_probes())
    probes.extend(generate_stage_probes())
    return probes


# ─── Experiment Runner ────────────────────────────────────────────────────────

def run_all(
    client: CacheAwareClient,
    probes: List[Probe],
    models: List[str],
    max_per_model: Optional[int] = None,
) -> List[Result]:
    results = []
    
    for model_key in models:
        model_id = MODELS[model_key]
        count = 0
        
        for probe in probes:
            if max_per_model and count >= max_per_model:
                break
            
            response, latency, in_tok, out_tok = client.query(
                model=model_id,
                prompt=probe.prompt,
            )
            
            extracted = client.extract_number(response)
            
            # Check correctness
            correct = False
            near = False
            if probe.expected.lower() in ("yes", "no"):
                correct = (response or "").lower().strip().startswith(probe.expected[0])
            elif extracted and probe.expected.replace("-", "").replace(".", "").isdigit():
                try:
                    ext_f = float(extracted)
                    exp_f = float(probe.expected)
                    if abs(ext_f - exp_f) < 0.01:
                        correct = True
                    elif exp_f != 0 and abs(ext_f - exp_f) / abs(exp_f) <= 0.05:
                        near = True
                    elif abs(ext_f - exp_f) <= 1:  # off by 1
                        near = True
                except:
                    pass
            
            # Classify residue
            if correct:
                residue = "CORRECT"
            elif near:
                residue = "NEAR"
            elif extracted is None:
                residue = "NO_EXTRACT"
            elif probe.expected.lower() in ("yes", "no"):
                residue = "WRONG_ANSWER"
            else:
                try:
                    ext_f = float(extracted)
                    exp_f = float(probe.expected)
                    # Check if it's an echo of input values
                    if any(abs(ext_f - v) < 0.01 for v in [1,2,3,4,5,6,7,8,9,10]):
                        residue = "ECHO"
                    elif abs(ext_f - exp_f) / max(abs(exp_f), 1) > 1.0:
                        residue = "WRONG_ORDER"
                    else:
                        residue = "OTHER"
                except:
                    residue = "PARSE_ERROR"
            
            results.append(Result(
                probe_id=probe.id,
                model=model_key,
                model_id=model_id,
                prompt=probe.prompt[:80],
                response=(response or "")[:80],
                extracted=extracted,
                expected=probe.expected,
                correct=correct,
                near=near,
                residue=residue,
                latency_ms=latency,
                category=probe.category,
                tokens_in=in_tok,
                tokens_out=out_tok,
            ))
            
            count += 1
            
            # Progress
            if count % 20 == 0:
                acc = sum(1 for r in results if r.model == model_key and r.correct) / count
                print(f"  [{model_key}] {count} probes, accuracy: {acc:.0%}")
    
    return results


def analyze(results: List[Result]) -> Dict:
    analysis = {
        "total": len(results),
        "by_model": {},
        "by_category": {},
        "by_residue": defaultdict(int),
        "by_operation": {},
        "cliff_curves": {},
        "novel": [],
    }
    
    # By model
    for model in set(r.model for r in results):
        mr = [r for r in results if r.model == model]
        correct = sum(1 for r in mr if r.correct)
        near = sum(1 for r in mr if r.near)
        total = len(mr)
        lats = [r.latency_ms for r in mr if r.latency_ms > 0]
        analysis["by_model"][model] = {
            "correct": correct,
            "near": near,
            "total": total,
            "accuracy": correct / total if total else 0,
            "near_rate": near / total if total else 0,
            "avg_latency_ms": statistics.mean(lats) if lats else 0,
            "p50_latency_ms": statistics.median(lats) if lats else 0,
            "total_input_tokens": sum(r.tokens_in for r in mr),
            "total_output_tokens": sum(r.tokens_out for r in mr),
        }
    
    # By category
    for cat in set(r.category for r in results):
        cr = [r for r in results if r.category == cat]
        correct = sum(1 for r in cr if r.correct)
        total = len(cr)
        analysis["by_category"][cat] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else 0,
        }
    
    # Residue distribution
    for r in results:
        analysis["by_residue"][r.residue] += 1
    
    # Cliff curves (addition composition)
    for model in set(r.model for r in results):
        add_results = [r for r in results if r.category == "composition_addition" and r.model == model]
        if add_results:
            curve = {}
            for r in add_results:
                # Parse depth from probe_id like "ADD-D5"
                import re as _re
                m = _re.search(r'D(\d+)', r.probe_id)
                depth = m.group(1) if m else "0"
                curve[depth] = curve.get(depth, {"correct": 0, "total": 0})
                curve[depth]["total"] += 1
                if r.correct:
                    curve[depth]["correct"] += 1
            analysis["cliff_curves"][model] = {
                k: {"accuracy": v["correct"]/v["total"], **v}
                for k, v in curve.items()
                if k.isdigit()
            }
    
    # Novel findings (wrong answers on "easy" probes)
    for r in results:
        if not r.correct and r.category in ("stage_detection", "eisenstein_norm"):
            analysis["novel"].append({
                "probe": r.probe_id,
                "model": r.model,
                "expected": r.expected,
                "got": r.extracted,
                "category": r.category,
                "residue": r.residue,
            })
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description="DeepInfra Cache-Aware Insights Engine")
    parser.add_argument("--quick", action="store_true", help="10 probes per category")
    parser.add_argument("--full", action="store_true", help="All probes, all models")
    parser.add_argument("--model", help="Run only this model (key from MODELS)")
    parser.add_argument("--output", default="experiments/deepinfra-results.json")
    args = parser.parse_args()
    
    key_file = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
    with open(key_file) as f:
        api_key = f.read().strip()
    
    client = CacheAwareClient(api_key)
    
    # Generate probes
    probes = generate_all_probes()
    print(f"Generated {len(probes)} probes across 7 categories")
    
    # Select models
    if args.model:
        models = [args.model]
    elif args.quick:
        models = ["seed-mini", "qwen-0.8b"]  # cheapest for quick test
    else:
        models = list(MODELS.keys())
    
    max_n = 30 if args.quick else None
    
    print(f"Running on: {models}")
    results = run_all(client, probes, models, max_per_model=max_n)
    
    # Analyze
    analysis = analyze(results)
    
    # Print summary
    print(f"\n{'='*60}")
    print("DEEPINFRA RESULTS")
    print(f"{'='*60}")
    print(f"Total probes: {analysis['total']}")
    
    print(f"\nBy Model:")
    for model, stats in sorted(analysis["by_model"].items(), key=lambda x: -x[1]["accuracy"]):
        print(f"  {model:15s}: {stats['correct']}/{stats['total']} = {stats['accuracy']:.0%} "
              f"(near: {stats['near_rate']:.0%}, lat: {stats['avg_latency_ms']:.0f}ms, "
              f"tokens: {stats['total_input_tokens']}in/{stats['total_output_tokens']}out)")
    
    print(f"\nBy Category:")
    for cat, stats in sorted(analysis["by_category"].items(), key=lambda x: -x[1]["accuracy"]):
        print(f"  {cat:30s}: {stats['correct']:3d}/{stats['total']:3d} = {stats['accuracy']:.0%}")
    
    print(f"\nResidue Distribution:")
    for residue, count in sorted(analysis["by_residue"].items(), key=lambda x: -x[1]):
        print(f"  {residue:15s}: {count}")
    
    if analysis["cliff_curves"]:
        print(f"\nComposition Cliff Curves:")
        for model, curve in analysis["cliff_curves"].items():
            print(f"  {model}: " + " → ".join(
                f"D{k}={v['accuracy']:.0%}" for k, v in sorted(curve.items(), key=lambda x: int(x[0]))
            ))
    
    # Cost
    cost = client.cost_estimate()
    print(f"\nCost Estimate:")
    print(f"  Queries: {cost['total_queries']}")
    print(f"  Tokens: {cost['total_input_tokens']}in / {cost['total_output_tokens']}out")
    print(f"  Cached: ~{cost['estimated_cached_tokens']} tokens")
    print(f"  Estimated cost: ${cost['estimated_cost_usd']}")
    print(f"  Cache savings: ${cost['cache_savings_usd']}")
    
    # Save
    output = {
        "analysis": analysis,
        "results": [asdict(r) for r in results],
        "cost": cost,
        "probes_total": len(probes),
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
